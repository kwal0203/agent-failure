#!/usr/bin/env bash
set -euo pipefail

# Bootstrap staging runtime secrets + GHCR pull secret from a local .env file.
#
# Required .env keys (direct or fallback):
#   DATABASE_URL_STAGING (or DATABASE_URL)
#   RUNTIME_SHARED_TOKEN_STAGING (or RUNTIME_SHARED_TOKEN)
#   AUTH_ISSUER_STAGING (or AUTH_ISSUER)
#   AUTH_AUDIENCE_STAGING (or AUTH_AUDIENCE)
#   AUTH_JWKS_URI_STAGING (or AUTH_JWKS_URI)
#   OPENROUTER_API_KEY_STAGING (or OPENROUTER_API_KEY)
#   GHCR_USERNAME
#   GHCR_TOKEN_STAGING (or GHCR_PAT or GHCR_TOKEN)
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

pick_var() {
  local preferred="$1"
  local fallback="$2"
  local outvar="$3"
  local sourcevar="$4"

  if [[ -n "${!preferred:-}" ]]; then
    printf -v "$outvar" '%s' "${!preferred}"
    printf -v "$sourcevar" '%s' "$preferred"
  elif [[ -n "${!fallback:-}" ]]; then
    printf -v "$outvar" '%s' "${!fallback}"
    printf -v "$sourcevar" '%s' "$fallback"
  else
    echo "Missing required env var in $ENV_FILE: $preferred (or $fallback)"
    exit 1
  fi
}

require_var GHCR_USERNAME

pick_var DATABASE_URL_STAGING DATABASE_URL EFFECTIVE_DATABASE_URL DB_SOURCE
pick_var RUNTIME_SHARED_TOKEN_STAGING RUNTIME_SHARED_TOKEN EFFECTIVE_RUNTIME_SHARED_TOKEN RUNTIME_TOKEN_SOURCE
pick_var AUTH_ISSUER_STAGING AUTH_ISSUER EFFECTIVE_AUTH_ISSUER AUTH_ISSUER_SOURCE
pick_var AUTH_AUDIENCE_STAGING AUTH_AUDIENCE EFFECTIVE_AUTH_AUDIENCE AUTH_AUDIENCE_SOURCE
pick_var AUTH_JWKS_URI_STAGING AUTH_JWKS_URI EFFECTIVE_AUTH_JWKS_URI AUTH_JWKS_URI_SOURCE
pick_var OPENROUTER_API_KEY_STAGING OPENROUTER_API_KEY EFFECTIVE_OPENROUTER_API_KEY OPENROUTER_SOURCE

if [[ -n "${GHCR_TOKEN_STAGING:-}" ]]; then
  GHCR_SECRET="$GHCR_TOKEN_STAGING"
  GHCR_SOURCE="GHCR_TOKEN_STAGING"
elif [[ -n "${GHCR_PAT:-}" ]]; then
  GHCR_SECRET="$GHCR_PAT"
  GHCR_SOURCE="GHCR_PAT"
elif [[ -n "${GHCR_TOKEN:-}" ]]; then
  GHCR_SECRET="$GHCR_TOKEN"
  GHCR_SOURCE="GHCR_TOKEN"
else
  echo "Missing required env var in $ENV_FILE: GHCR_TOKEN_STAGING (or GHCR_PAT or GHCR_TOKEN)"
  exit 1
fi

GHCR_EMAIL="${GHCR_EMAIL:-noreply@example.com}"

echo "Using namespace: $NS"
echo "Using DATABASE_URL from: $DB_SOURCE"
echo "Using RUNTIME_SHARED_TOKEN from: $RUNTIME_TOKEN_SOURCE"
echo "Using AUTH_ISSUER from: $AUTH_ISSUER_SOURCE"
echo "Using AUTH_AUDIENCE from: $AUTH_AUDIENCE_SOURCE"
echo "Using AUTH_JWKS_URI from: $AUTH_JWKS_URI_SOURCE"
echo "Using OPENROUTER_API_KEY from: $OPENROUTER_SOURCE"
echo "Using GHCR secret from: $GHCR_SOURCE"

kubectl get ns "$NS" >/dev/null 2>&1 || kubectl create ns "$NS" >/dev/null

echo "Applying runtime-secrets..."
kubectl -n "$NS" create secret generic runtime-secrets \
  --from-literal=DATABASE_URL="$EFFECTIVE_DATABASE_URL" \
  --from-literal=RUNTIME_SHARED_TOKEN="$EFFECTIVE_RUNTIME_SHARED_TOKEN" \
  --from-literal=AUTH_ISSUER="$EFFECTIVE_AUTH_ISSUER" \
  --from-literal=AUTH_AUDIENCE="$EFFECTIVE_AUTH_AUDIENCE" \
  --from-literal=AUTH_JWKS_URI="$EFFECTIVE_AUTH_JWKS_URI" \
  --from-literal=OPENROUTER_API_KEY="$EFFECTIVE_OPENROUTER_API_KEY" \
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
