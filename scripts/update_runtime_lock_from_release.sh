#!/usr/bin/env bash
set -euo pipefail

# Append new active runtime lock entries from release artifact while preserving history.
# Existing active entries for target labs are marked revoked.
#
# Usage:
#   ./scripts/update_runtime_lock_from_release.sh
#
# Optional:
#   ARTIFACT_DIR=.artifacts
#   RELEASE_ENV_FILE=.artifacts/runtime-image-release.env
#   LOCK_FILE=deploy/k8s/staging/runtime-image.lock
#   TARGET_LABS=prompt-injection,tool-misuse,memory-poisoning

ARTIFACT_DIR="${ARTIFACT_DIR:-.artifacts}"
RELEASE_ENV_FILE="${RELEASE_ENV_FILE:-${ARTIFACT_DIR}/runtime-image-release.env}"
LOCK_FILE="${LOCK_FILE:-deploy/k8s/staging/runtime-image.lock}"
TARGET_LABS="${TARGET_LABS:-prompt-injection,tool-misuse,memory-poisoning}"

if [[ ! -f "${RELEASE_ENV_FILE}" ]]; then
  echo "Missing release artifact: ${RELEASE_ENV_FILE}" >&2
  echo "Run scripts/push_runtime_image.sh first." >&2
  exit 1
fi

if [[ ! -f "${LOCK_FILE}" ]]; then
  echo "Missing runtime lock file: ${LOCK_FILE}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${RELEASE_ENV_FILE}"

required_vars=(
  IMAGE_BASE
  IMAGE_DIGEST_REF
  GIT_SHA
  BUILD_TS
)

for v in "${required_vars[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "Required variable missing in ${RELEASE_ENV_FILE}: ${v}" >&2
    exit 1
  fi
done

if [[ "${IMAGE_DIGEST_REF}" != *@sha256:* ]]; then
  echo "IMAGE_DIGEST_REF is not digest-pinned: ${IMAGE_DIGEST_REF}" >&2
  exit 1
fi

IMAGE_DIGEST="${IMAGE_DIGEST_REF##*@}"

# Build entry blocks that should be inserted immediately after `images:`.
entry_blocks=""
IFS=',' read -r -a labs_arr <<< "${TARGET_LABS}"
for lab in "${labs_arr[@]}"; do
  entry_blocks+="  - lab_slug: ${lab}"$'\n'
  entry_blocks+="    lab_version: \"v1\""$'\n'
  entry_blocks+="    image_repo: \"${IMAGE_BASE}\""$'\n'
  entry_blocks+="    image_digest: \"${IMAGE_DIGEST}\""$'\n'
  entry_blocks+="    image_ref: \"${IMAGE_DIGEST_REF}\""$'\n'
  entry_blocks+="    build_git_sha: \"${GIT_SHA}\""$'\n'
  entry_blocks+="    built_at_utc: \"${BUILD_TS}\""$'\n'
  entry_blocks+="    status: \"active\""$'\n'
done

TMP_FILE="$(mktemp)"
trap 'rm -f "${TMP_FILE}"' EXIT

awk \
  -v target_labs="${TARGET_LABS}" \
  -v new_entries="${entry_blocks}" \
  '
  BEGIN {
    n = split(target_labs, arr, ",");
    for (i = 1; i <= n; i++) {
      labs[arr[i]] = 1;
    }
    current_slug = "";
    in_target = 0;
    inserted = 0;
  }

  /^images:[[:space:]]*$/ {
    print;
    if (!inserted) {
      printf "%s", new_entries;
      inserted = 1;
    }
    next;
  }

  /^  - lab_slug:/ {
    current_slug = $3;
    in_target = (current_slug in labs);
    print;
    next;
  }

  {
    if (in_target && /^    status:[[:space:]]*"active"/) {
      print "    status: \"revoked\"";
      next;
    }
    print;
  }

  END {
    if (!inserted) {
      print "Could not find images: section in lock file." > "/dev/stderr";
      exit 2;
    }
  }
  ' "${LOCK_FILE}" > "${TMP_FILE}"

mv "${TMP_FILE}" "${LOCK_FILE}"

echo "Appended new runtime lock entries in ${LOCK_FILE}"
echo "  image_ref=${IMAGE_DIGEST_REF}"
echo "  build_git_sha=${GIT_SHA}"
echo "  built_at_utc=${BUILD_TS}"
echo "  target_labs=${TARGET_LABS}"
