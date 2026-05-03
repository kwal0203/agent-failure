#!/usr/bin/env bash
set -euo pipefail

# Build/push control-plane image, run DB migrations against production DB,
# and trigger Render deploys for API + worker services.
#
# Usage:
#   RENDER_API_KEY=... \
#   RENDER_CONTROL_PLANE_SERVICE_ID=... \
#   RENDER_EVALUATOR_WORKER_SERVICE_ID=... \
#   RENDER_PROVISIONING_WORKER_SERVICE_ID=... \
#   RENDER_CLEANUP_WORKER_SERVICE_ID=... \
#   RENDER_SESSION_OBJECTIVE_COMPLETED_WORKER_SERVICE_ID=... \
#   RENDER_SESSION_HINT_UNLOCK_WORKER_SERVICE_ID=... \
#   RENDER_SESSION_COMPLETED_WORKER_SERVICE_ID=... \
#   RENDER_SESSION_FEEDBACK_CREATED_WORKER_SERVICE_ID=... \
#   DATABASE_URL='postgresql+psycopg://...?...' \
#   ./scripts/release_render.sh
#
# Optional:
#   SKIP_MIGRATIONS=1
#   SKIP_BUILD_PUSH=1
#   RENDER_API_BASE_URL=https://api.render.com/v1

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_FILE="${ROOT_DIR}/.artifacts/control-plane-image-release.env"
RENDER_API_BASE_URL="${RENDER_API_BASE_URL:-https://api.render.com/v1}"
SKIP_MIGRATIONS="${SKIP_MIGRATIONS:-0}"
SKIP_BUILD_PUSH="${SKIP_BUILD_PUSH:-0}"

cd "${ROOT_DIR}"

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 1
  fi
}

deploy_render_service() {
  local service_id="$1"
  local service_label="$2"
  local response http_code deploy_id

  response="$(
    curl -sS -X POST \
      -H "Authorization: Bearer ${RENDER_API_KEY}" \
      -H "Accept: application/json" \
      "${RENDER_API_BASE_URL}/services/${service_id}/deploys" \
      -w $'\n%{http_code}'
  )"

  http_code="$(echo "${response}" | tail -n 1)"
  if [[ "${http_code}" != "200" && "${http_code}" != "201" ]]; then
    echo "Render deploy failed for ${service_label} (service_id=${service_id}, status=${http_code})" >&2
    echo "Response: $(echo "${response}" | head -n -1)" >&2
    exit 1
  fi

  deploy_id="$(RESPONSE_JSON="$(echo "${response}" | head -n -1)" uv run python - <<'PY'
import json
import os

raw = os.environ.get("RESPONSE_JSON", "").strip()
if not raw:
    print("")
    raise SystemExit(0)
try:
    payload = json.loads(raw)
except json.JSONDecodeError:
    print("")
    raise SystemExit(0)
print(payload.get("id", ""))
PY
)"

  if [[ -n "${deploy_id}" ]]; then
    echo "Triggered ${service_label}: deploy_id=${deploy_id}"
  else
    echo "Triggered ${service_label}"
  fi
}

echo "[1/4] Validating release configuration..."
require_env RENDER_API_KEY
require_env RENDER_CONTROL_PLANE_SERVICE_ID
require_env RENDER_EVALUATOR_WORKER_SERVICE_ID
require_env RENDER_PROVISIONING_WORKER_SERVICE_ID
require_env RENDER_CLEANUP_WORKER_SERVICE_ID
require_env RENDER_SESSION_OBJECTIVE_COMPLETED_WORKER_SERVICE_ID
require_env RENDER_SESSION_HINT_UNLOCK_WORKER_SERVICE_ID
require_env RENDER_SESSION_COMPLETED_WORKER_SERVICE_ID
require_env RENDER_SESSION_FEEDBACK_CREATED_WORKER_SERVICE_ID

if [[ "${SKIP_BUILD_PUSH}" != "1" ]]; then
  echo "[2/4] Building + pushing control-plane image..."
  ./scripts/build_control_plane_image.sh
  ./scripts/push_control_plane_image.sh
else
  echo "[2/4] Skipping build/push (SKIP_BUILD_PUSH=1)..."
fi

if [[ ! -f "${ARTIFACT_FILE}" ]]; then
  echo "Missing artifact file: ${ARTIFACT_FILE}" >&2
  echo "Run scripts/build_control_plane_image.sh and scripts/push_control_plane_image.sh first, or unset SKIP_BUILD_PUSH." >&2
  exit 1
fi

# shellcheck disable=SC1090
source "${ARTIFACT_FILE}"
if [[ -n "${IMAGE_DIGEST_REF:-}" ]]; then
  echo "Using image digest: ${IMAGE_DIGEST_REF}"
fi

if [[ "${SKIP_MIGRATIONS}" != "1" ]]; then
  echo "[3/4] Running Alembic migrations against DATABASE_URL..."
  require_env DATABASE_URL
  uv run alembic upgrade head
else
  echo "[3/4] Skipping migrations (SKIP_MIGRATIONS=1)..."
fi

echo "[4/4] Triggering Render deploys..."
deploy_render_service "${RENDER_CONTROL_PLANE_SERVICE_ID}" "control-plane"
deploy_render_service "${RENDER_EVALUATOR_WORKER_SERVICE_ID}" "evaluator-worker"
deploy_render_service "${RENDER_PROVISIONING_WORKER_SERVICE_ID}" "provisioning-worker"
deploy_render_service "${RENDER_CLEANUP_WORKER_SERVICE_ID}" "cleanup-worker"
deploy_render_service "${RENDER_SESSION_OBJECTIVE_COMPLETED_WORKER_SERVICE_ID}" "session-objective-completed-worker"
deploy_render_service "${RENDER_SESSION_HINT_UNLOCK_WORKER_SERVICE_ID}" "session-hint-unlock-worker"
deploy_render_service "${RENDER_SESSION_COMPLETED_WORKER_SERVICE_ID}" "session-completed-worker"
deploy_render_service "${RENDER_SESSION_FEEDBACK_CREATED_WORKER_SERVICE_ID}" "session-feedback-created-worker"

echo "Done."
