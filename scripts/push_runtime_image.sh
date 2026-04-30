#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/push_runtime_image.sh
#
# Prereq:
#   scripts/build_runtime_image.sh has already run and created:
#   .artifacts/runtime-image-build.env
#
# Optional:
#   ARTIFACT_DIR=.artifacts
#   UPDATE_RUNTIME_LOCK=1
#   LOCK_FILE=deploy/k8s/staging/runtime-image.lock
#   TARGET_LABS=agent-prompt-injection,agent-tool-misuse,agent-memory-poisoning

ARTIFACT_DIR="${ARTIFACT_DIR:-.artifacts}"
BUILD_ENV_FILE="${ARTIFACT_DIR}/runtime-image-build.env"
RELEASE_ENV_FILE="${ARTIFACT_DIR}/runtime-image-release.env"

if [[ ! -f "${BUILD_ENV_FILE}" ]]; then
  echo "Missing build artifact: ${BUILD_ENV_FILE}" >&2
  echo "Run scripts/build_runtime_image.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${BUILD_ENV_FILE}"

required_vars=(
  IMAGE_BASE
  IMAGE_VERSION
  IMAGE_SHA
  LAB_SLUG
  LAB_VERSION
  GIT_SHA
  BUILD_TS
)

for v in "${required_vars[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "Required variable missing in ${BUILD_ENV_FILE}: ${v}" >&2
    exit 1
  fi
done

echo "Pushing runtime image tags..."
echo "  ${IMAGE_VERSION}"
echo "  ${IMAGE_SHA}"

docker push "${IMAGE_VERSION}"
docker push "${IMAGE_SHA}"

if ! docker buildx version >/dev/null 2>&1; then
  echo "docker buildx is required to resolve remote digest." >&2
  exit 1
fi

DIGEST="$(docker buildx imagetools inspect "${IMAGE_SHA}" --format '{{json .Manifest.Digest}}' | tr -d '\"')"
if [[ -z "${DIGEST}" ]]; then
  echo "Could not resolve pushed image digest for ${IMAGE_SHA}." >&2
  exit 1
fi
DIGEST_REF="${IMAGE_BASE}@${DIGEST}"

mkdir -p "${ARTIFACT_DIR}"
cat > "${RELEASE_ENV_FILE}" <<EOF
IMAGE_BASE=${IMAGE_BASE}
IMAGE_VERSION=${IMAGE_VERSION}
IMAGE_SHA=${IMAGE_SHA}
IMAGE_DIGEST_REF=${DIGEST_REF}
LAB_SLUG=${LAB_SLUG}
LAB_VERSION=${LAB_VERSION}
GIT_SHA=${GIT_SHA}
BUILD_TS=${BUILD_TS}
PUSHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

echo "Push complete."
echo "Digest pinned reference:"
echo "  ${DIGEST_REF}"
echo "Wrote release artifact: ${RELEASE_ENV_FILE}"

if [[ "${UPDATE_RUNTIME_LOCK:-0}" == "1" ]]; then
  LOCK_FILE="${LOCK_FILE:-deploy/k8s/staging/runtime-image.lock}"
  TARGET_LABS="${TARGET_LABS:-agent-prompt-injection,agent-tool-misuse,agent-memory-poisoning}"
  ./scripts/update_runtime_lock_from_release.sh
  ./scripts/validate_runtime_lock.sh
else
  echo
  echo "Next step (optional):"
  echo "  UPDATE_RUNTIME_LOCK=1 ./scripts/push_runtime_image.sh"
  echo "or run:"
  echo "  ./scripts/update_runtime_lock_from_release.sh"
fi
