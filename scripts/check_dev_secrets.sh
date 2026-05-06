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

echo "Namespace: $NS"

check_secret_key runtime-secrets DATABASE_URL
check_secret_key runtime-secrets RUNTIME_SHARED_TOKEN
check_secret_key runtime-secrets AUTH_ISSUER
check_secret_key runtime-secrets AUTH_AUDIENCE
check_secret_key runtime-secrets AUTH_JWKS_URI
check_secret_key runtime-secrets OPENROUTER_API_KEY

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
