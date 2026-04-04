#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# Run runtime container locally using pinned digest from release artifact.
#
# Usage:
#   ./scripts/run_runtime_local.sh
#
# Prereq:
#   ./scripts/build_runtime_image.sh
#   ./scripts/push_runtime_image.sh
#   (creates .artifacts/runtime-image-release.env with IMAGE_DIGEST_REF)
#
# Optional overrides:
#   HOST_PORT=8001
#   CONTAINER_PORT=8000
#   RUNTIME_SHARED_TOKEN=dev-secret
#   MODEL_CLIENT_MODE=gateway
#   PROVIDER_ENDPOINT=https://openrouter.ai/api/v1/chat/completions
#   MODEL_NAME=deepseek/deepseek-v3.2
#   CONTAINER_NAME=agent-failure-runtime-local
#   ARTIFACT_DIR=.artifacts
#   PULL=1

HOST_PORT="${HOST_PORT:-8001}"
CONTAINER_PORT="${CONTAINER_PORT:-8000}"
RUNTIME_SHARED_TOKEN="${RUNTIME_SHARED_TOKEN:-dev-secret}"
MODEL_CLIENT_MODE="${MODEL_CLIENT_MODE:-gateway}"
PROVIDER_ENDPOINT="${PROVIDER_ENDPOINT:-https://openrouter.ai/api/v1/chat/completions}"
MODEL_NAME="${MODEL_NAME:-deepseek/deepseek-v3.2}"
CONTAINER_NAME="${CONTAINER_NAME:-agent-failure-runtime-local}"
ARTIFACT_DIR="${ARTIFACT_DIR:-.artifacts}"
PULL="${PULL:-1}"
RELEASE_ENV_FILE="${ARTIFACT_DIR}/runtime-image-release.env"

if [[ ! -f "${RELEASE_ENV_FILE}" ]]; then
  echo "Missing release artifact: ${RELEASE_ENV_FILE}" >&2
  echo "Run scripts/build_runtime_image.sh and scripts/push_runtime_image.sh first." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${RELEASE_ENV_FILE}"
if [[ -z "${IMAGE_DIGEST_REF:-}" ]]; then
  echo "IMAGE_DIGEST_REF missing in ${RELEASE_ENV_FILE}" >&2
  exit 1
fi

if [[ -z "${OPENROUTER_API_KEY:-}" && -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env"
  set +a
fi

if [[ "${MODEL_CLIENT_MODE}" == "gateway" && -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "OPENROUTER_API_KEY is required when MODEL_CLIENT_MODE=gateway." >&2
  exit 1
fi

if [[ "${PULL}" == "1" ]]; then
  echo "Pulling image digest: ${IMAGE_DIGEST_REF}"
  docker pull "${IMAGE_DIGEST_REF}" >/dev/null
fi

# Replace any stale container with same name.
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

echo "Starting runtime container:"
echo "  image: ${IMAGE_DIGEST_REF}"
echo "  port:  ${HOST_PORT}:${CONTAINER_PORT}"
echo "  mode:  ${MODEL_CLIENT_MODE}"
echo "  model: ${MODEL_NAME}"

exec docker run --rm \
  --name "${CONTAINER_NAME}" \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  -e RUNTIME_SHARED_TOKEN="${RUNTIME_SHARED_TOKEN}" \
  -e MODEL_CLIENT_MODE="${MODEL_CLIENT_MODE}" \
  -e PROVIDER_ENDPOINT="${PROVIDER_ENDPOINT}" \
  -e OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}" \
  -e MODEL_NAME="${MODEL_NAME}" \
  "${IMAGE_DIGEST_REF}"
