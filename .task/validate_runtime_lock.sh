#!/usr/bin/env bash
set -euo pipefail

LOCK_FILE="${1}"
TARGET_LABS="${2}"

IFS=',' read -r -a labs_arr <<< "${TARGET_LABS}"
for lab in "${labs_arr[@]}"; do
  lab_trimmed="$(echo "${lab}" | xargs)"
  [[ -z "${lab_trimmed}" ]] && continue
  entry="$(awk -v slug="${lab_trimmed}" -v ver="v1" '
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
      if (!found) { print "NOT FOUND: " slug " " ver > "/dev/stderr"; exit 2 }
    }
  ' "${LOCK_FILE}")"
  status="$(printf '%s' "${entry}" | awk -F': ' '/status:/{gsub(/"/,"",$2); print $2; exit}')"
  image_ref="$(printf '%s' "${entry}" | awk -F': ' '/image_ref:/{gsub(/"/,"",$2); print $2; exit}')"
  if [[ "${status}" != "active" ]]; then
    echo "${lab_trimmed} is not active (status=${status})" >&2; exit 1
  fi
  if [[ "${image_ref}" != *@sha256:* ]]; then
    echo "${lab_trimmed} is not digest-pinned: ${image_ref}" >&2; exit 1
  fi
  echo "  ${lab_trimmed} (v1) -> ${image_ref}"
done
