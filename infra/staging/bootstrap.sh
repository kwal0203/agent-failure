#!/usr/bin/env bash
set -euo pipefail

command -v kubectl >/dev/null 2>&1 || { echo "kubectl not found"; exit 1; }

SECRETS_FILE="deploy/k8s/staging/.secrets.local"
if [[ -f "$SECRETS_FILE" ]]; then
  set -a
  source "$SECRETS_FILE"
  set +a
else
  echo "missing $SECRETS_FILE (needed for ghcr-pull secret)"
  exit 1
fi

: "${GHCR_USER:?GHCR_USER is required in $SECRETS_FILE}"
: "${GHCR_PAT:?GHCR_PAT is required in $SECRETS_FILE}"

echo "[1/5] Applying namespaces..."
kubectl apply -f deploy/k8s/staging/namespaces.yaml

kubectl wait --for=create serviceaccount/default -n control-plane --timeout=60s
kubectl wait --for=create serviceaccount/default -n runtime-pool --timeout=60s

echo "[2/5] Applying runtime image pull secret..."
kubectl -n runtime-pool create secret docker-registry ghcr-pull \
  --docker-server=ghcr.io \
  --docker-username="${GHCR_USER}" \
  --docker-password="${GHCR_PAT}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "[3/5] Applying control-plane config/secret..."
kubectl apply -f deploy/k8s/staging/control-plane-config.yaml

echo "[4/5] Applying runtime smoke pod..."
kubectl apply -f deploy/k8s/staging/runtime-smoke-pod.yaml

echo "[5/5] Verifying..."
kubectl get ns control-plane runtime-pool
kubectl -n runtime-pool get pod runtime-smoke

echo "Bootstrap complete."
