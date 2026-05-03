#!/usr/bin/env bash
set -euo pipefail

# Recreate a kind cluster on VPS with host NodePort mapping for control-plane API
# and re-apply staging manifests/secrets used by this repo.
#
# Usage (full recreate):
#   GHCR_USERNAME=kwal0203 \
#   GHCR_TOKEN=... \
#   GHCR_EMAIL=you@example.com \
#   OPENROUTER_API_KEY=... \
#   RUNTIME_SHARED_TOKEN=... \
#   ./scripts/bootstrap_vps_kind_staging.sh
#
# Usage (reuse existing cluster + existing secrets):
#   RECREATE_CLUSTER=0 ./scripts/bootstrap_vps_kind_staging.sh
#
# Optional:
#   FORCE_SECRET_UPDATE=1    # force overwrite ghcr-pull/runtime-secrets
#
# Notes:
# - This deletes and recreates the kind cluster named agent-failure-staging.
# - Existing in-cluster state is lost.
# - Requires: kind, kubectl

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER_NAME="${CLUSTER_NAME:-agent-failure-staging}"
KIND_CONFIG_PATH="${KIND_CONFIG_PATH:-/tmp/kind-agent-failure-staging.yaml}"
RECREATE_CLUSTER="${RECREATE_CLUSTER:-1}"
FORCE_SECRET_UPDATE="${FORCE_SECRET_UPDATE:-0}"

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 1
  fi
}

secret_exists() {
  local name="$1"
  kubectl -n runtime-pool get secret "${name}" >/dev/null 2>&1
}

if ! command -v kind >/dev/null 2>&1; then
  echo "kind not found in PATH" >&2
  exit 1
fi

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl not found in PATH" >&2
  exit 1
fi

cat > "${KIND_CONFIG_PATH}" <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: ${CLUSTER_NAME}
nodes:
  - role: control-plane
    extraPortMappings:
      - containerPort: 30080
        hostPort: 30080
        protocol: TCP
EOF

if [[ "${RECREATE_CLUSTER}" == "1" ]]; then
  echo "[1/7] Recreating kind cluster: ${CLUSTER_NAME}"
  kind delete cluster --name "${CLUSTER_NAME}" || true
  kind create cluster --config "${KIND_CONFIG_PATH}"
else
  echo "[1/7] Reusing existing cluster: ${CLUSTER_NAME}"
fi

echo "[2/7] Verifying cluster context"
kubectl cluster-info --context "kind-${CLUSTER_NAME}"
kubectl get nodes

echo "[3/7] Applying namespace + RBAC"
cd "${ROOT_DIR}"
kubectl apply -f deploy/k8s/staging/namespaces.yaml
kubectl apply -f deploy/k8s/staging/control-plane-worker-rbac.yaml

if [[ "${FORCE_SECRET_UPDATE}" == "1" || "${RECREATE_CLUSTER}" == "1" ]] || ! secret_exists ghcr-pull; then
  require_env GHCR_USERNAME
  require_env GHCR_TOKEN
  require_env GHCR_EMAIL
  echo "[4/7] Creating/updating image pull secret"
  kubectl -n runtime-pool create secret docker-registry ghcr-pull \
    --docker-server=ghcr.io \
    --docker-username="${GHCR_USERNAME}" \
    --docker-password="${GHCR_TOKEN}" \
    --docker-email="${GHCR_EMAIL}" \
    --dry-run=client -o yaml | kubectl apply -f -
else
  echo "[4/7] Reusing existing image pull secret (ghcr-pull)"
fi

if [[ "${FORCE_SECRET_UPDATE}" == "1" || "${RECREATE_CLUSTER}" == "1" ]] || ! secret_exists runtime-secrets; then
  require_env OPENROUTER_API_KEY
  require_env RUNTIME_SHARED_TOKEN
  echo "[5/7] Creating/updating runtime secrets"
  kubectl -n runtime-pool create secret generic runtime-secrets \
    --from-literal=OPENROUTER_API_KEY="${OPENROUTER_API_KEY}" \
    --from-literal=RUNTIME_SHARED_TOKEN="${RUNTIME_SHARED_TOKEN}" \
    --dry-run=client -o yaml | kubectl apply -f -
else
  echo "[5/7] Reusing existing runtime secrets (runtime-secrets)"
fi

echo "[6/7] Applying staging manifests"
kubectl apply -k deploy/k8s/staging

echo "[7/7] Waiting for deployments"
kubectl -n runtime-pool rollout status deploy/control-plane --timeout=300s || true
kubectl -n runtime-pool get deploy,pods,svc

echo
echo "Done."
echo "If using Caddy on the host, set upstream to 172.17.0.1:30080."
