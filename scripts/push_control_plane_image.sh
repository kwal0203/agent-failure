#!/usr/bin/env bash
set -euo pipefail

# Push control-plane image tags and write a pinned digest artifact.
#
# Usage:
#   ./scripts/push_control_plane_image.sh
#
# Prereq:
#   scripts/build_control_plane_image.sh has already run and created:
#   .artifacts/control-plane-image-build.env
#
# Optional:
#   ARTIFACT_DIR=.artifacts

ARTIFACT_DIR="${ARTIFACT_DIR:-.artifacts}"
BUILD_ENV_FILE="${ARTIFACT_DIR}/control-plane-image-build.env"
RELEASE_ENV_FILE="${ARTIFACT_DIR}/control-plane-image-release.env"

if [[ ! -f "${BUILD_ENV_FILE}" ]]; then
  echo "Missing build artifact: ${BUILD_ENV_FILE}" >&2
  echo "Run scripts/build_control_plane_image.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${BUILD_ENV_FILE}"

required_vars=(
  IMAGE_BASE
  IMAGE_VERSION
  IMAGE_SHA
  CONTROL_PLANE_VERSION
  GIT_SHA
  BUILD_TS
)

for v in "${required_vars[@]}"; do
  if [[ -z "${!v:-}" ]]; then
    echo "Required variable missing in ${BUILD_ENV_FILE}: ${v}" >&2
    exit 1
  fi
done

echo "Pushing control-plane image tags..."
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
CONTROL_PLANE_VERSION=${CONTROL_PLANE_VERSION}
GIT_SHA=${GIT_SHA}
BUILD_TS=${BUILD_TS}
PUSHED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EOF

echo "Push complete."
echo "Digest pinned reference:"
echo "  ${DIGEST_REF}"
echo "Wrote release artifact: ${RELEASE_ENV_FILE}"
