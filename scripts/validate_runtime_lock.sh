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
#   TARGET_LABS=agent-prompt-injection,agent-tool-misuse,agent-memory-poisoning

LOCK_FILE="${LOCK_FILE:-deploy/k8s/staging/runtime-image.lock}"
SELECTION_FILE="${SELECTION_FILE:-deploy/k8s/staging/runtime-image-selection.yaml}"
TARGET_LABS="${TARGET_LABS:-}"

if [[ ! -f "${LOCK_FILE}" ]]; then
  echo "Missing lock file: ${LOCK_FILE}" >&2
  exit 1
fi

if [[ -z "${TARGET_LABS}" && ! -f "${SELECTION_FILE}" ]]; then
  echo "Missing selection file: ${SELECTION_FILE}" >&2
  exit 1
fi

find_entry_block() {
  local slug="$1"
  local ver="$2"
  awk -v slug="${slug}" -v ver="${ver}" '
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
  ' "${LOCK_FILE}" || true
}

validate_entry() {
  local slug="$1"
  local ver="$2"
  local entry_block status image_ref
  entry_block="$(find_entry_block "${slug}" "${ver}")"

  if [[ -z "${entry_block}" ]]; then
    echo "Selection not found in lock file: ${slug} ${ver}" >&2
    return 1
  fi

  status="$(printf '%s' "${entry_block}" | awk -F': ' '/status:/{gsub(/"/,"",$2); print $2; exit}')"
  image_ref="$(printf '%s' "${entry_block}" | awk -F': ' '/image_ref:/{gsub(/"/,"",$2); print $2; exit}')"

  if [[ "${status}" != "active" ]]; then
    echo "Selected image is not active for ${slug} (status=${status})." >&2
    return 1
  fi

  if [[ "${image_ref}" != *@sha256:* ]]; then
    echo "Selected image is not digest-pinned for ${slug}: ${image_ref}" >&2
    return 1
  fi

  echo "  ${slug} (${ver}) -> ${image_ref}"
}

if [[ -n "${TARGET_LABS}" ]]; then
  echo "Runtime image lock validation passed (TARGET_LABS mode)."
  IFS=',' read -r -a labs_arr <<< "${TARGET_LABS}"
  for lab in "${labs_arr[@]}"; do
    lab_trimmed="$(echo "${lab}" | xargs)"
    [[ -z "${lab_trimmed}" ]] && continue
    validate_entry "${lab_trimmed}" "v1"
  done
  exit 0
fi

# Default selection mode.
default_lab_slug="$(awk -F': ' '/^default_lab_slug:/{gsub(/"/,"",$2); print $2}' "${SELECTION_FILE}")"
default_lab_version="$(awk -F': ' '/^default_lab_version:/{gsub(/"/,"",$2); print $2}' "${SELECTION_FILE}")"

if [[ -z "${default_lab_slug}" || -z "${default_lab_version}" ]]; then
  echo "Selection file missing default_lab_slug/default_lab_version." >&2
  exit 1
fi

validate_entry "${default_lab_slug}" "${default_lab_version}"

echo "Runtime image lock validation passed."
echo "  default_lab_slug=${default_lab_slug}"
echo "  default_lab_version=${default_lab_version}"
