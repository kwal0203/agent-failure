#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_FILE="${ROOT_DIR}/.artifacts/control-plane-image-release.env"
KUSTOMIZATION_FILE="${ROOT_DIR}/deploy/k8s/staging/kustomization.yaml"
CONTROL_PLANE_IMAGE="ghcr.io/kwal0203/agent-failure-control-plane"

cd "${ROOT_DIR}"

echo "[1/5] Releasing default runtime image..."
./scripts/release_runtime_image.sh

echo "[2/5] Releasing agent runtime image set..."
LAB_SLUG=agent TARGET_LABS=agent-prompt-injection,agent-tool-misuse,agent-memory-poisoning \
  ./scripts/release_runtime_image.sh

echo "[3/5] Building control-plane image..."
./scripts/build_control_plane_image.sh

echo "[4/5] Pushing control-plane image..."
./scripts/push_control_plane_image.sh

if [[ ! -f "${ARTIFACT_FILE}" ]]; then
  echo "Missing artifact file: ${ARTIFACT_FILE}" >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${ARTIFACT_FILE}"

if [[ -z "${IMAGE_DIGEST_REF:-}" ]]; then
  echo "IMAGE_DIGEST_REF is missing in ${ARTIFACT_FILE}" >&2
  exit 1
fi

if [[ "${IMAGE_DIGEST_REF}" != "${CONTROL_PLANE_IMAGE}"@sha256:* ]]; then
  echo "Unexpected IMAGE_DIGEST_REF format: ${IMAGE_DIGEST_REF}" >&2
  exit 1
fi

NEW_DIGEST="${IMAGE_DIGEST_REF##*@}"

if [[ ! -f "${KUSTOMIZATION_FILE}" ]]; then
  echo "Missing kustomization file: ${KUSTOMIZATION_FILE}" >&2
  exit 1
fi

echo "[5/5] Updating staging kustomization digest to ${NEW_DIGEST}..."
tmp_file="$(mktemp)"
trap 'rm -f "${tmp_file}"' EXIT

awk -v image_name="${CONTROL_PLANE_IMAGE}" -v new_digest="${NEW_DIGEST}" '
  BEGIN {
    in_images = 0
    in_target = 0
    updated = 0
  }
  /^images:[[:space:]]*$/ {
    in_images = 1
    print
    next
  }
  in_images && /^[^[:space:]]/ {
    in_images = 0
    in_target = 0
  }
  in_images && $0 ~ "^[[:space:]]*-[[:space:]]*name:[[:space:]]*" image_name "[[:space:]]*$" {
    in_target = 1
    print
    next
  }
  in_images && in_target && $0 ~ "^[[:space:]]*digest:[[:space:]]*sha256:[0-9a-f]+[[:space:]]*$" {
    sub(/digest:[[:space:]]*sha256:[0-9a-f]+/, "digest: " new_digest)
    updated = 1
    in_target = 0
    print
    next
  }
  in_images && in_target && $0 ~ "^[[:space:]]*-[[:space:]]*name:" {
    in_target = 0
  }
  {
    print
  }
  END {
    if (updated != 1) {
      print "Failed to update digest for image: " image_name > "/dev/stderr"
      exit 1
    }
  }
' "${KUSTOMIZATION_FILE}" > "${tmp_file}"

mv "${tmp_file}" "${KUSTOMIZATION_FILE}"
trap - EXIT

echo "[6/6] Applying staging manifests..."
./scripts/apply_control_plane_staging.sh

echo "Done. Updated ${KUSTOMIZATION_FILE} with digest ${NEW_DIGEST} and applied staging."
