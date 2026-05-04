#!/usr/bin/env bash
set -euo pipefail

KUSTOMIZATION_FILE="${1}"
CONTROL_PLANE_IMAGE="${2}"
NEW_DIGEST="${3}"

tmp_file="$(mktemp)"
trap 'rm -f "${tmp_file}"' EXIT

awk -v image_name="${CONTROL_PLANE_IMAGE}" -v new_digest="${NEW_DIGEST}" '
  BEGIN { in_images = 0; in_target = 0; updated = 0 }
  /^images:[[:space:]]*$/ { in_images = 1; print; next }
  in_images && /^[^[:space:]]/ { in_images = 0; in_target = 0 }
  in_images && $0 ~ "^[[:space:]]*-[[:space:]]*name:[[:space:]]*" image_name "[[:space:]]*$" { in_target = 1; print; next }
  in_images && in_target && $0 ~ "^[[:space:]]*digest:[[:space:]]*sha256:[0-9a-f]+[[:space:]]*$" {
    sub(/digest:[[:space:]]*sha256:[0-9a-f]+/, "digest: " new_digest)
    updated = 1; in_target = 0; print; next
  }
  in_images && in_target && $0 ~ "^[[:space:]]*-[[:space:]]*name:" { in_target = 0 }
  { print }
  END { if (updated != 1) { print "Failed to update digest for: " image_name > "/dev/stderr"; exit 1 } }
' "${KUSTOMIZATION_FILE}" > "${tmp_file}"

mv "${tmp_file}" "${KUSTOMIZATION_FILE}"
trap - EXIT
echo "Updated kustomization digest to ${NEW_DIGEST}"
