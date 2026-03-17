#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/scan_runtime_image.sh
#   IMAGE_REF=ghcr.io/kane/agent-failure-runtime-v1:v1-baseline-0.1.0 ./scripts/scan_runtime_image.sh
#
# Defaults:
#   - loads .artifacts/runtime-image-build.env if present
#   - scans IMAGE_VERSION by default

ARTIFACT_DIR="${ARTIFACT_DIR:-.artifacts}"
BUILD_ENV_FILE="${ARTIFACT_DIR}/runtime-image-build.env"

if [[ -f "${BUILD_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${BUILD_ENV_FILE}"
fi

if ! command -v trivy >/dev/null 2>&1; then
  echo "trivy not found. Install trivy before running scan." >&2
  exit 1
fi

IMAGE_REF="${IMAGE_REF:-${IMAGE_VERSION:-}}"
if [[ -z "${IMAGE_REF}" ]]; then
  echo "IMAGE_REF is required (or run build script first to populate IMAGE_VERSION)." >&2
  exit 1
fi

SEVERITY="${SEVERITY:-CRITICAL}"   # tighten later to HIGH,CRITICAL if needed
TRIVY_TIMEOUT="${TRIVY_TIMEOUT:-5m}"
REPORT_FILE="${ARTIFACT_DIR}/runtime-image-scan.txt"

mkdir -p "${ARTIFACT_DIR}"

echo "Scanning image: ${IMAGE_REF}"
echo "Severity gate: ${SEVERITY}"

# Human-readable report artifact (non-gating output)
trivy image \
  --timeout "${TRIVY_TIMEOUT}" \
  --severity "${SEVERITY}" \
  --no-progress \
  "${IMAGE_REF}" | tee "${REPORT_FILE}"

# Gating check: fail if vulnerabilities at/above severity exist
trivy image \
  --timeout "${TRIVY_TIMEOUT}" \
  --severity "${SEVERITY}" \
  --exit-code 1 \
  --no-progress \
  "${IMAGE_REF}" >/dev/null

echo "Scan passed (no ${SEVERITY} vulnerabilities found)."
echo "Report: ${REPORT_FILE}"
