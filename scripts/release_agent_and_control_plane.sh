#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_FILE="${ROOT_DIR}/.artifacts/control-plane-image-release.env"
KUSTOMIZATION_FILE="${ROOT_DIR}/deploy/k8s/staging/kustomization.yaml"
SELECTION_FILE="${ROOT_DIR}/deploy/k8s/staging/runtime-image-selection.yaml"
CONTROL_PLANE_IMAGE="ghcr.io/kwal0203/agent-failure-control-plane"
AGENT_TARGET_LABS="agent-prompt-injection,agent-tool-misuse,agent-memory-poisoning"

cd "${ROOT_DIR}"

echo "[1/8] Releasing agent runtime image set..."
LAB_SLUG=agent TARGET_LABS="${AGENT_TARGET_LABS}" UPDATE_RUNTIME_LOCK=1 ./scripts/release_runtime_image.sh

echo "[2/8] Validating runtime lock..."
TARGET_LABS="${AGENT_TARGET_LABS}" ./scripts/validate_runtime_lock.sh

if [[ ! -f "${SELECTION_FILE}" ]]; then
  echo "Missing runtime image selection file: ${SELECTION_FILE}" >&2
  exit 1
fi

echo "[3/8] Setting default runtime selection to agent-prompt-injection..."
cat > "${SELECTION_FILE}" <<EOF
default_lab_slug: agent-prompt-injection
default_lab_version: "v1"
EOF

echo "[4/8] Building control-plane image..."
./scripts/build_control_plane_image.sh

echo "[5/8] Pushing control-plane image..."
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

echo "[6/8] Updating staging kustomization digest to ${NEW_DIGEST}..."
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

echo "[7/8] Applying staging manifests..."
./scripts/apply_control_plane_staging.sh

echo "[8/8] Waiting for control-plane rollout..."
kubectl rollout status deploy/control-plane -n runtime-pool --timeout=300s

echo "Done. Updated runtime lock + selection, updated ${KUSTOMIZATION_FILE} with digest ${NEW_DIGEST}, applied staging, and confirmed control-plane rollout."
