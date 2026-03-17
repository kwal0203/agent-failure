#!/usr/bin/env bash
set -euo pipefail

# Validates:
# - default selection exists in lock file
# - selected entry is active
# - selected image is digest-pinned (@sha256:...)
#
# Usage:
#   ./scripts/validate_runtime_lock.sh
#
# Optional:
#   LOCK_FILE=deploy/k8s/staging/runtime-image.lock
#   SELECTION_FILE=deploy/k8s/staging/runtime-image-selection.yaml

LOCK_FILE="${LOCK_FILE:-deploy/k8s/staging/runtime-image.lock}"
SELECTION_FILE="${SELECTION_FILE:-deploy/k8s/staging/runtime-image-selection.yaml}"

if [[ ! -f "${LOCK_FILE}" ]]; then
  echo "Missing lock file: ${LOCK_FILE}" >&2
  exit 1
fi

if [[ ! -f "${SELECTION_FILE}" ]]; then
  echo "Missing selection file: ${SELECTION_FILE}" >&2
  exit 1
fi

# Minimal YAML parsing via awk/sed for current simple schema.
default_lab_slug="$(awk -F': ' '/^default_lab_slug:/{gsub(/"/,"",$2); print $2}' "${SELECTION_FILE}")"
default_lab_version="$(awk -F': ' '/^default_lab_version:/{gsub(/"/,"",$2); print $2}' "${SELECTION_FILE}")"

if [[ -z "${default_lab_slug}" || -z "${default_lab_version}" ]]; then
  echo "Selection file missing default_lab_slug/default_lab_version." >&2
  exit 1
fi

# Grab block lines for matching image entry.
entry_block="$(awk -v slug="${default_lab_slug}" -v ver="${default_lab_version}" '
  /^images:/ {in_images=1; next}
  in_images && /^  - / {
    if (block != "") {
      if (block ~ "lab_slug: " slug "\n" && block ~ "lab_version: \"" ver "\"") { print block; found=1; exit }
    }
    block = ""
  }
  in_images { block = block $0 "\n" }
  END {
    if (!found && block != "" && block ~ "lab_slug: " slug "\n" && block ~ "lab_version: \"" ver "\"") { print block; found=1 }
    if (!found) exit 2
  }
' "${LOCK_FILE}" || true)"

if [[ -z "${entry_block}" ]]; then
  echo "Default selection not found in lock file: ${default_lab_slug} ${default_lab_version}" >&2
  exit 1
fi

status="$(printf '%s' "${entry_block}" | awk -F': ' '/status:/{gsub(/"/,"",$2); print $2; exit}')"
image_ref="$(printf '%s' "${entry_block}" | awk -F': ' '/image_ref:/{gsub(/"/,"",$2); print $2; exit}')"

if [[ "${status}" != "active" ]]; then
  echo "Default selected image is not active (status=${status})." >&2
  exit 1
fi

if [[ "${image_ref}" != *@sha256:* ]]; then
  echo "Default selected image is not digest-pinned: ${image_ref}" >&2
  exit 1
fi

echo "Runtime image lock validation passed."
echo "  default_lab_slug=${default_lab_slug}"
echo "  default_lab_version=${default_lab_version}"
echo "  image_ref=${image_ref}"
