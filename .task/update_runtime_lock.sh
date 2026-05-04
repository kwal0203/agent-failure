#!/usr/bin/env bash
set -euo pipefail

LOCK_FILE="${1}"
IMAGE_BASE="${2}"
IMAGE_DIGEST_REF="${3}"
GIT_SHA="${4}"
BUILD_TS="${5}"
TARGET_LABS="${6}"

IMAGE_DIGEST="${IMAGE_DIGEST_REF##*@}"

entry_blocks=""
IFS=',' read -r -a labs_arr <<< "${TARGET_LABS}"
for lab in "${labs_arr[@]}"; do
  lab_trimmed="$(echo "${lab}" | xargs)"
  [[ -z "${lab_trimmed}" ]] && continue
  entry_blocks+="  - lab_slug: ${lab_trimmed}"$'\n'
  entry_blocks+="    lab_version: \"v1\""$'\n'
  entry_blocks+="    image_repo: \"${IMAGE_BASE}\""$'\n'
  entry_blocks+="    image_digest: \"${IMAGE_DIGEST}\""$'\n'
  entry_blocks+="    image_ref: \"${IMAGE_DIGEST_REF}\""$'\n'
  entry_blocks+="    build_git_sha: \"${GIT_SHA}\""$'\n'
  entry_blocks+="    built_at_utc: \"${BUILD_TS}\""$'\n'
  entry_blocks+="    status: \"active\""$'\n'
done

cat > "${LOCK_FILE}" <<EOF
apiVersion: agent-failure/v1alpha1
kind: RuntimeImageLock
metadata:
  environment: staging
images:
${entry_blocks}
EOF

echo "Updated ${LOCK_FILE}"
