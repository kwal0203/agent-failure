#!/usr/bin/env bash
set -euo pipefail

# Overwrite runtime lock entries for target labs using the current release artifact.
# This keeps only latest active references instead of preserving historical entries.
#
# Usage:
#   ./scripts/update_runtime_lock_from_release.sh
#
# Optional:
#   ARTIFACT_DIR=.artifacts
#   RELEASE_ENV_FILE=.artifacts/runtime-image-release.env
#   LOCK_FILE=deploy/k8s/staging/runtime-image.lock
#   TARGET_LABS=agent-prompt-injection,agent-tool-misuse,agent-memory-poisoning

ARTIFACT_DIR="${ARTIFACT_DIR:-.artifacts}"
RELEASE_ENV_FILE="${RELEASE_ENV_FILE:-${ARTIFACT_DIR}/runtime-image-release.env}"
LOCK_FILE="${LOCK_FILE:-deploy/k8s/staging/runtime-image.lock}"
TARGET_LABS="${TARGET_LABS:-agent-prompt-injection,agent-tool-misuse,agent-memory-poisoning}"

if [[ ! -f "${RELEASE_ENV_FILE}" ]]; then
  echo "Missing release artifact: ${RELEASE_ENV_FILE}" >&2
  echo "Run scripts/push_runtime_image.sh first." >&2
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

mkdir -p "$(dirname "${LOCK_FILE}")"

# Build entry blocks for the lock file.
entry_blocks=""
IFS=',' read -r -a labs_arr <<< "${TARGET_LABS}"
for lab in "${labs_arr[@]}"; do
  lab_trimmed="$(echo "${lab}" | xargs)"
  if [[ -z "${lab_trimmed}" ]]; then
    continue
  fi
  entry_blocks+="  - lab_slug: ${lab_trimmed}"$'\n'
  entry_blocks+="    lab_version: \"v1\""$'\n'
  entry_blocks+="    image_repo: \"${IMAGE_BASE}\""$'\n'
  entry_blocks+="    image_digest: \"${IMAGE_DIGEST}\""$'\n'
  entry_blocks+="    image_ref: \"${IMAGE_DIGEST_REF}\""$'\n'
  entry_blocks+="    build_git_sha: \"${GIT_SHA}\""$'\n'
  entry_blocks+="    built_at_utc: \"${BUILD_TS}\""$'\n'
  entry_blocks+="    status: \"active\""$'\n'
done

if [[ -z "${entry_blocks}" ]]; then
  echo "No target labs resolved from TARGET_LABS=${TARGET_LABS}" >&2
  exit 1
fi

cat > "${LOCK_FILE}" <<EOF
apiVersion: agent-failure/v1alpha1
kind: RuntimeImageLock
metadata:
  environment: staging
images:
${entry_blocks}
EOF

echo "Overwrote runtime lock entries in ${LOCK_FILE}"
echo "  image_ref=${IMAGE_DIGEST_REF}"
echo "  build_git_sha=${GIT_SHA}"
echo "  built_at_utc=${BUILD_TS}"
echo "  target_labs=${TARGET_LABS}"
