#!/usr/bin/env bash
set -euo pipefail

# Build control-plane image from repo-root context.
#
# Usage:
#   ./scripts/build_control_plane_image.sh
#
# Optional overrides:
#   REGISTRY=ghcr.io
#   ORG=kwal0203
#   IMAGE_REPO=agent-failure-control-plane
#   CONTROL_PLANE_VERSION=0.1.0
#   DOCKERFILE_PATH=apps/control_plane/Dockerfile
#   ARTIFACT_DIR=.artifacts

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

REGISTRY="${REGISTRY:-ghcr.io}"
ORG="${ORG:-kwal0203}"
IMAGE_REPO="${IMAGE_REPO:-agent-failure-control-plane}"
CONTROL_PLANE_VERSION="${CONTROL_PLANE_VERSION:-0.1.0}"
DOCKERFILE_PATH="${DOCKERFILE_PATH:-apps/control_plane/Dockerfile}"
ARTIFACT_DIR="${ARTIFACT_DIR:-.artifacts}"

if [[ ! -f "${DOCKERFILE_PATH}" ]]; then
  echo "Dockerfile not found: ${DOCKERFILE_PATH}" >&2
  exit 1
fi

GIT_SHA="$(git rev-parse --short HEAD)"
BUILD_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

IMAGE_BASE="${REGISTRY}/${ORG}/${IMAGE_REPO}"
TAG_VERSION="v1-control-plane-${CONTROL_PLANE_VERSION}"
TAG_SHA="sha-${GIT_SHA}"
IMAGE_VERSION="${IMAGE_BASE}:${TAG_VERSION}"
IMAGE_SHA="${IMAGE_BASE}:${TAG_SHA}"

echo "Building control-plane image..."
echo "  Dockerfile: ${DOCKERFILE_PATH}"
echo "  Context:    ${REPO_ROOT}"
echo "  Tags:"
echo "    ${IMAGE_VERSION}"
echo "    ${IMAGE_SHA}"

docker build \
  -f "${DOCKERFILE_PATH}" \
  -t "${IMAGE_VERSION}" \
  -t "${IMAGE_SHA}" \
  --label org.opencontainers.image.source="agent-failure" \
  --label org.opencontainers.image.revision="${GIT_SHA}" \
  --label org.opencontainers.image.created="${BUILD_TS}" \
  .

mkdir -p "${ARTIFACT_DIR}"
cat > "${ARTIFACT_DIR}/control-plane-image-build.env" <<EOF
REGISTRY=${REGISTRY}
ORG=${ORG}
IMAGE_REPO=${IMAGE_REPO}
CONTROL_PLANE_VERSION=${CONTROL_PLANE_VERSION}
GIT_SHA=${GIT_SHA}
BUILD_TS=${BUILD_TS}
IMAGE_BASE=${IMAGE_BASE}
IMAGE_VERSION=${IMAGE_VERSION}
IMAGE_SHA=${IMAGE_SHA}
DOCKERFILE_PATH=${DOCKERFILE_PATH}
EOF

echo "Build complete."
echo "Wrote build metadata: ${ARTIFACT_DIR}/control-plane-image-build.env"
