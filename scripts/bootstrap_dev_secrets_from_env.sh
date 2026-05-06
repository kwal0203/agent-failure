#!/usr/bin/env bash
set -euo pipefail

# Bootstrap runtime secrets + GHCR pull secret from a local .env file.
#
# Required .env keys:
#   DATABASE_URL (or DATABASE_URL_DEV)
#   RUNTIME_SHARED_TOKEN
#   AUTH_ISSUER
#   AUTH_AUDIENCE
#   AUTH_JWKS_URI
#   OPENROUTER_API_KEY
#   GHCR_USERNAME
#   GHCR_PAT or GHCR_TOKEN_DEV or GHCR_TOKEN
#
# Optional:
#   GHCR_EMAIL (defaults to noreply@example.com)

NS="${NS:-runtime-pool}"
ENV_FILE="${1:-.env}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 2
  }
}

need kubectl

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Env file not found: $ENV_FILE"
  exit 2
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required env var in $ENV_FILE: $name"
    exit 1
  fi
}

require_var RUNTIME_SHARED_TOKEN
require_var AUTH_ISSUER
require_var AUTH_AUDIENCE
require_var AUTH_JWKS_URI
require_var OPENROUTER_API_KEY
require_var GHCR_USERNAME

if [[ -n "${DATABASE_URL_DEV:-}" ]]; then
  EFFECTIVE_DATABASE_URL="$DATABASE_URL_DEV"
  DB_SOURCE="DATABASE_URL_DEV"
elif [[ -n "${DATABASE_URL:-}" ]]; then
  EFFECTIVE_DATABASE_URL="$DATABASE_URL"
  DB_SOURCE="DATABASE_URL"
else
  echo "Missing required env var in $ENV_FILE: DATABASE_URL_DEV (or DATABASE_URL)"
  exit 1
fi

if [[ -n "${GHCR_PAT:-}" ]]; then
  GHCR_SECRET="$GHCR_PAT"
elif [[ -n "${GHCR_TOKEN_DEV:-}" ]]; then
  GHCR_SECRET="$GHCR_TOKEN_DEV"
elif [[ -n "${GHCR_TOKEN:-}" ]]; then
  GHCR_SECRET="$GHCR_TOKEN"
else
  echo "Missing required env var in $ENV_FILE: GHCR_PAT (or GHCR_TOKEN_DEV or GHCR_TOKEN)"
  exit 1
fi

GHCR_EMAIL="${GHCR_EMAIL:-noreply@example.com}"

echo "Using namespace: $NS"
echo "Using database URL source: $DB_SOURCE"
kubectl get ns "$NS" >/dev/null 2>&1 || kubectl create ns "$NS" >/dev/null

echo "Applying runtime-secrets..."
kubectl -n "$NS" create secret generic runtime-secrets \
  --from-literal=DATABASE_URL="$EFFECTIVE_DATABASE_URL" \
  --from-literal=RUNTIME_SHARED_TOKEN="$RUNTIME_SHARED_TOKEN" \
  --from-literal=AUTH_ISSUER="$AUTH_ISSUER" \
  --from-literal=AUTH_AUDIENCE="$AUTH_AUDIENCE" \
  --from-literal=AUTH_JWKS_URI="$AUTH_JWKS_URI" \
  --from-literal=OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Applying ghcr-pull image pull secret..."
kubectl -n "$NS" create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io \
  --docker-username="$GHCR_USERNAME" \
  --docker-password="$GHCR_SECRET" \
  --docker-email="$GHCR_EMAIL" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Applying ghcr-creds image pull secret (compat)..."
kubectl -n "$NS" create secret docker-registry ghcr-creds \
  --docker-server=ghcr.io \
  --docker-username="$GHCR_USERNAME" \
  --docker-password="$GHCR_SECRET" \
  --docker-email="$GHCR_EMAIL" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Patching default service account imagePullSecrets..."
kubectl -n "$NS" patch serviceaccount default \
  --type='merge' \
  -p '{"imagePullSecrets":[{"name":"ghcr-pull"},{"name":"ghcr-creds"}]}' >/dev/null

echo "Done."
echo "Secrets in $NS:"
kubectl -n "$NS" get secrets | rg "runtime-secrets|ghcr-pull|ghcr-creds" || true

echo ""
echo "Next:"
echo "  kubectl -n $NS rollout restart deploy"
echo "  kubectl -n $NS get pods -w"
