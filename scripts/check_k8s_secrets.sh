#!/usr/bin/env bash
set -euo pipefail

NS="${NS:-runtime-pool}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 2
  }
}

need kubectl

fail=0

check_secret_key() {
  local secret="$1"
  local key="$2"

  if ! kubectl -n "$NS" get secret "$secret" >/dev/null 2>&1; then
    echo "[FAIL] secret missing: $secret"
    fail=1
    return
  fi

  local raw
  raw="$(kubectl -n "$NS" get secret "$secret" -o "jsonpath={.data.$key}" 2>/dev/null || true)"
  if [[ -z "$raw" ]]; then
    echo "[FAIL] $secret missing key: $key"
    fail=1
    return
  fi

  local decoded
  decoded="$(printf "%s" "$raw" | base64 -d 2>/dev/null || true)"
  if [[ -z "$decoded" ]]; then
    echo "[FAIL] $secret key empty/invalid: $key"
    fail=1
    return
  fi

  echo "[OK]   $secret.$key present"
}

check_secret_key_optional() {
  local secret="$1"
  local key="$2"

  if ! kubectl -n "$NS" get secret "$secret" >/dev/null 2>&1; then
    echo "[WARN] secret missing (optional key skipped): $secret"
    return
  fi

  local raw
  raw="$(kubectl -n "$NS" get secret "$secret" -o "jsonpath={.data.$key}" 2>/dev/null || true)"
  if [[ -z "$raw" ]]; then
    echo "[WARN] $secret missing optional key: $key"
    return
  fi

  local decoded
  decoded="$(printf "%s" "$raw" | base64 -d 2>/dev/null || true)"
  if [[ -z "$decoded" ]]; then
    echo "[WARN] $secret optional key empty/invalid: $key"
    return
  fi

  echo "[OK]   $secret.$key present (optional)"
}

echo "Namespace: $NS"

check_secret_key runtime-secrets DATABASE_URL
check_secret_key runtime-secrets RUNTIME_SHARED_TOKEN
check_secret_key runtime-secrets AUTH_ISSUER
check_secret_key runtime-secrets AUTH_AUDIENCE
check_secret_key runtime-secrets AUTH_JWKS_URI
check_secret_key runtime-secrets OPENROUTER_API_KEY
check_secret_key runtime-secrets ENROLLMENT_TOKEN_SECRET
check_secret_key runtime-secrets ENROLLMENT_TOKEN_TTL_SECONDS

check_secret_key runtime-secrets PILOT_ALERT_EMAIL_ENABLED
check_secret_key runtime-secrets PILOT_ALERT_EMAIL_SMTP_HOST
check_secret_key runtime-secrets PILOT_ALERT_EMAIL_SMTP_PORT
check_secret_key runtime-secrets PILOT_ALERT_EMAIL_SMTP_USERNAME
check_secret_key runtime-secrets PILOT_ALERT_EMAIL_SMTP_PASSWORD
check_secret_key runtime-secrets PILOT_ALERT_EMAIL_SMTP_STARTTLS
check_secret_key runtime-secrets PILOT_ALERT_EMAIL_FROM
check_secret_key runtime-secrets PILOT_ALERT_EMAIL_TO

check_secret_key runtime-secrets PILOT_PROVISIONING_EMAIL_ENABLED
check_secret_key runtime-secrets PILOT_PROVISIONING_EMAIL_SMTP_HOST
check_secret_key runtime-secrets PILOT_PROVISIONING_EMAIL_SMTP_PORT
check_secret_key runtime-secrets PILOT_PROVISIONING_EMAIL_SMTP_USERNAME
check_secret_key runtime-secrets PILOT_PROVISIONING_EMAIL_SMTP_PASSWORD
check_secret_key runtime-secrets PILOT_PROVISIONING_EMAIL_SMTP_STARTTLS
check_secret_key runtime-secrets PILOT_PROVISIONING_EMAIL_FROM
check_secret_key runtime-secrets PILOT_PROVISIONING_EMAIL_ADMIN_TO
check_secret_key runtime-secrets PILOT_PROVISIONING_ONBOARDING_LOGIN_URL
check_secret_key_optional runtime-secrets PILOT_PROVISIONING_ONBOARDING_QUICKSTART_URL

check_secret_key runtime-secrets INSTRUCTOR_PROVISIONING_ENABLED
check_secret_key runtime-secrets COGNITO_USER_POOL_ID
check_secret_key runtime-secrets COGNITO_REGION
check_secret_key runtime-secrets COGNITO_INSTRUCTOR_GROUP_NAME

if kubectl -n "$NS" get secret ghcr-pull >/dev/null 2>&1; then
  echo "[OK]   ghcr-pull present"
else
  echo "[FAIL] secret missing: ghcr-pull"
  fail=1
fi

if kubectl -n "$NS" get secret ghcr-creds >/dev/null 2>&1; then
  echo "[OK]   ghcr-creds present (compat)"
else
  echo "[WARN] ghcr-creds missing (compat secret not present)"
fi

if kubectl -n "$NS" get sa default -o jsonpath='{.imagePullSecrets[*].name}' | grep -qw ghcr-pull; then
  echo "[OK]   default serviceaccount references ghcr-pull"
else
  echo "[FAIL] default serviceaccount missing imagePullSecrets entry for ghcr-pull"
  fail=1
fi

if (( fail )); then
  echo "Summary: FAIL"
  exit 1
fi

echo "Summary: PASS"
