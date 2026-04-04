#!/usr/bin/env bash
set -euo pipefail

# Build runtime image from repo-root context.
#
# Usage:
#   ./scripts/build_runtime_image.sh
#
# Optional overrides:
#   REGISTRY=ghcr.io
#   ORG=kane
#   IMAGE_REPO=agent-failure-runtime-v1
#   LAB_SLUG=baseline
#   LAB_VERSION=0.1.0
#   RUNTIME_DIR=runtimes/baseline
#   ARTIFACT_DIR=.artifacts

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

REGISTRY="${REGISTRY:-ghcr.io}"
ORG="${ORG:-kwal0203}"
IMAGE_REPO="${IMAGE_REPO:-agent-failure-runtime-v1}"
LAB_SLUG="${LAB_SLUG:-baseline}"
LAB_VERSION="${LAB_VERSION:-0.1.0}"
RUNTIME_DIR="${RUNTIME_DIR:-runtimes/${LAB_SLUG}}"
ARTIFACT_DIR="${ARTIFACT_DIR:-.artifacts}"

DOCKERFILE_PATH="${RUNTIME_DIR}/Dockerfile"
if [[ ! -f "${DOCKERFILE_PATH}" ]]; then
  echo "Dockerfile not found: ${DOCKERFILE_PATH}" >&2
  exit 1
fi

GIT_SHA="$(git rev-parse --short HEAD)"
BUILD_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

IMAGE_BASE="${REGISTRY}/${ORG}/${IMAGE_REPO}"
TAG_VERSION="v1-${LAB_SLUG}-${LAB_VERSION}"
TAG_SHA="sha-${GIT_SHA}"
IMAGE_VERSION="${IMAGE_BASE}:${TAG_VERSION}"
IMAGE_SHA="${IMAGE_BASE}:${TAG_SHA}"

echo "Building runtime image..."
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
  --label io.agent-failure.lab.slug="${LAB_SLUG}" \
  --label io.agent-failure.lab.version="${LAB_VERSION}" \
  .

mkdir -p "${ARTIFACT_DIR}"
cat > "${ARTIFACT_DIR}/runtime-image-build.env" <<EOF
REGISTRY=${REGISTRY}
ORG=${ORG}
IMAGE_REPO=${IMAGE_REPO}
LAB_SLUG=${LAB_SLUG}
LAB_VERSION=${LAB_VERSION}
GIT_SHA=${GIT_SHA}
BUILD_TS=${BUILD_TS}
IMAGE_BASE=${IMAGE_BASE}
IMAGE_VERSION=${IMAGE_VERSION}
IMAGE_SHA=${IMAGE_SHA}
DOCKERFILE_PATH=${DOCKERFILE_PATH}
EOF

echo "Build complete."
echo "Wrote build metadata: ${ARTIFACT_DIR}/runtime-image-build.env"
