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

# Resolve canonical digest from remote image metadata.
# RepoDigests returns entries like: ghcr.io/org/repo@sha256:...
DIGEST_REF="$(docker image inspect "${IMAGE_SHA}" --format '{{index .RepoDigests 0}}' 2>/dev/null || true)"

if [[ -z "${DIGEST_REF}" ]]; then
  echo "Failed to resolve digest from local metadata; trying docker buildx imagetools..." >&2
  if command -v docker >/dev/null 2>&1 && docker buildx version >/dev/null 2>&1; then
    DIGEST="$(docker buildx imagetools inspect "${IMAGE_SHA}" --format '{{json .Manifest.Digest}}' | tr -d '\"')"
    if [[ -n "${DIGEST}" ]]; then
      DIGEST_REF="${IMAGE_BASE}@${DIGEST}"
    fi
  fi
fi

if [[ -z "${DIGEST_REF}" ]]; then
  echo "Could not resolve pushed image digest for ${IMAGE_SHA}" >&2
  exit 1
fi

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
