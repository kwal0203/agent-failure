#!/usr/bin/env bash
set -euo pipefail

# Bootstrap Kubernetes runtime secrets + GHCR pull secret from a local .env file.
#
# Required .env keys:
#   DATABASE_URL
#   RUNTIME_SHARED_TOKEN
#   AUTH_ISSUER
#   AUTH_AUDIENCE
#   AUTH_JWKS_URI
#   OPENROUTER_API_KEY
#   AWS_ACCESS_KEY_ID
#   AWS_SECRET_ACCESS_KEY
#   AWS_DEFAULT_REGION
#   ENROLLMENT_TOKEN_SECRET
#   ENROLLMENT_TOKEN_TTL_SECONDS
#   GHCR_USERNAME
#   GHCR_TOKEN
#   GHCR_EMAIL

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

require_var DATABASE_URL
require_var RUNTIME_SHARED_TOKEN
require_var AUTH_ISSUER
require_var AUTH_AUDIENCE
require_var AUTH_JWKS_URI
require_var OPENROUTER_API_KEY
require_var AWS_ACCESS_KEY_ID
require_var AWS_SECRET_ACCESS_KEY
require_var AWS_DEFAULT_REGION
require_var ENROLLMENT_TOKEN_SECRET
require_var ENROLLMENT_TOKEN_TTL_SECONDS
require_var GHCR_USERNAME
require_var GHCR_TOKEN
require_var GHCR_EMAIL

if [[ "${PILOT_ALERT_EMAIL_ENABLED:-false}" == "true" ]]; then
  require_var PILOT_ALERT_EMAIL_SMTP_HOST
  require_var PILOT_ALERT_EMAIL_SMTP_PORT
  require_var PILOT_ALERT_EMAIL_SMTP_USERNAME
  require_var PILOT_ALERT_EMAIL_SMTP_PASSWORD
  require_var PILOT_ALERT_EMAIL_SMTP_STARTTLS
  require_var PILOT_ALERT_EMAIL_FROM
  require_var PILOT_ALERT_EMAIL_TO
fi

if [[ "${INSTRUCTOR_PROVISIONING_ENABLED:-false}" == "true" ]]; then
  require_var COGNITO_USER_POOL_ID
  require_var COGNITO_REGION
  require_var COGNITO_INSTRUCTOR_GROUP_NAME
fi

if [[ "${PILOT_PROVISIONING_EMAIL_ENABLED:-false}" == "true" ]]; then
  require_var PILOT_PROVISIONING_EMAIL_SMTP_HOST
  require_var PILOT_PROVISIONING_EMAIL_SMTP_PORT
  require_var PILOT_PROVISIONING_EMAIL_SMTP_USERNAME
  require_var PILOT_PROVISIONING_EMAIL_SMTP_PASSWORD
  require_var PILOT_PROVISIONING_EMAIL_SMTP_STARTTLS
  require_var PILOT_PROVISIONING_EMAIL_FROM
  require_var PILOT_PROVISIONING_EMAIL_ADMIN_TO
  require_var PILOT_PROVISIONING_ONBOARDING_LOGIN_URL
fi

echo "Using namespace: $NS"

kubectl get ns "$NS" >/dev/null 2>&1 || kubectl create ns "$NS" >/dev/null

echo "Applying runtime-secrets..."
kubectl -n "$NS" create secret generic runtime-secrets \
  --from-literal=DATABASE_URL="$DATABASE_URL" \
  --from-literal=RUNTIME_SHARED_TOKEN="$RUNTIME_SHARED_TOKEN" \
  --from-literal=AUTH_ISSUER="$AUTH_ISSUER" \
  --from-literal=AUTH_AUDIENCE="$AUTH_AUDIENCE" \
  --from-literal=AUTH_JWKS_URI="$AUTH_JWKS_URI" \
  --from-literal=OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
  --from-literal=AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  --from-literal=AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  --from-literal=AWS_DEFAULT_REGION="$AWS_DEFAULT_REGION" \
  --from-literal=ENROLLMENT_TOKEN_SECRET="$ENROLLMENT_TOKEN_SECRET" \
  --from-literal=ENROLLMENT_TOKEN_TTL_SECONDS="$ENROLLMENT_TOKEN_TTL_SECONDS" \
  --from-literal=PILOT_ALERT_EMAIL_ENABLED="${PILOT_ALERT_EMAIL_ENABLED:-false}" \
  --from-literal=PILOT_ALERT_EMAIL_SMTP_HOST="${PILOT_ALERT_EMAIL_SMTP_HOST:-}" \
  --from-literal=PILOT_ALERT_EMAIL_SMTP_PORT="${PILOT_ALERT_EMAIL_SMTP_PORT:-}" \
  --from-literal=PILOT_ALERT_EMAIL_SMTP_USERNAME="${PILOT_ALERT_EMAIL_SMTP_USERNAME:-}" \
  --from-literal=PILOT_ALERT_EMAIL_SMTP_PASSWORD="${PILOT_ALERT_EMAIL_SMTP_PASSWORD:-}" \
  --from-literal=PILOT_ALERT_EMAIL_SMTP_STARTTLS="${PILOT_ALERT_EMAIL_SMTP_STARTTLS:-}" \
  --from-literal=PILOT_ALERT_EMAIL_FROM="${PILOT_ALERT_EMAIL_FROM:-}" \
  --from-literal=PILOT_ALERT_EMAIL_TO="${PILOT_ALERT_EMAIL_TO:-}" \
  --from-literal=PILOT_PROVISIONING_EMAIL_ENABLED="${PILOT_PROVISIONING_EMAIL_ENABLED:-false}" \
  --from-literal=PILOT_PROVISIONING_EMAIL_SMTP_HOST="${PILOT_PROVISIONING_EMAIL_SMTP_HOST:-}" \
  --from-literal=PILOT_PROVISIONING_EMAIL_SMTP_PORT="${PILOT_PROVISIONING_EMAIL_SMTP_PORT:-}" \
  --from-literal=PILOT_PROVISIONING_EMAIL_SMTP_USERNAME="${PILOT_PROVISIONING_EMAIL_SMTP_USERNAME:-}" \
  --from-literal=PILOT_PROVISIONING_EMAIL_SMTP_PASSWORD="${PILOT_PROVISIONING_EMAIL_SMTP_PASSWORD:-}" \
  --from-literal=PILOT_PROVISIONING_EMAIL_SMTP_STARTTLS="${PILOT_PROVISIONING_EMAIL_SMTP_STARTTLS:-}" \
  --from-literal=PILOT_PROVISIONING_EMAIL_FROM="${PILOT_PROVISIONING_EMAIL_FROM:-}" \
  --from-literal=PILOT_PROVISIONING_EMAIL_ADMIN_TO="${PILOT_PROVISIONING_EMAIL_ADMIN_TO:-}" \
  --from-literal=PILOT_PROVISIONING_ONBOARDING_LOGIN_URL="${PILOT_PROVISIONING_ONBOARDING_LOGIN_URL:-}" \
  --from-literal=PILOT_PROVISIONING_ONBOARDING_QUICKSTART_URL="${PILOT_PROVISIONING_ONBOARDING_QUICKSTART_URL:-}" \
  --from-literal=INSTRUCTOR_PROVISIONING_ENABLED="${INSTRUCTOR_PROVISIONING_ENABLED:-false}" \
  --from-literal=COGNITO_USER_POOL_ID="${COGNITO_USER_POOL_ID:-}" \
  --from-literal=COGNITO_REGION="${COGNITO_REGION:-}" \
  --from-literal=COGNITO_INSTRUCTOR_GROUP_NAME="${COGNITO_INSTRUCTOR_GROUP_NAME:-}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Applying ghcr-pull image pull secret..."
kubectl -n "$NS" create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io \
  --docker-username="$GHCR_USERNAME" \
  --docker-password="$GHCR_TOKEN" \
  --docker-email="$GHCR_EMAIL" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Applying ghcr-creds image pull secret (compat)..."
kubectl -n "$NS" create secret docker-registry ghcr-creds \
  --docker-server=ghcr.io \
  --docker-username="$GHCR_USERNAME" \
  --docker-password="$GHCR_TOKEN" \
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
