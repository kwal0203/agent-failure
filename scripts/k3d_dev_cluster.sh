#!/usr/bin/env bash
set -euo pipefail

# Safe local k3d dev cluster manager.
# - Uses a dedicated cluster name/context.
# - Uses explicit ports to avoid accidental overlap.
# - Refuses risky operations when current context is staging-like.

CLUSTER_NAME="${CLUSTER_NAME:-agent-failure-dev}"
KUBECONTEXT="k3d-${CLUSTER_NAME}"
API_PORT="${API_PORT:-6550}"
HTTP_PORT="${HTTP_PORT:-18080}"
NAMESPACE="${NAMESPACE:-runtime-pool}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 2
  }
}

need k3d
need kubectl

current_ctx="$(kubectl config current-context 2>/dev/null || true)"

is_staging_context() {
  local ctx="$1"
  [[ "$ctx" == *"staging"* || "$ctx" == *"prod"* || "$ctx" == *"runtime"* ]]
}

usage() {
  cat <<EOF
Usage: $0 <create|delete|use|status>

Env overrides:
  CLUSTER_NAME (default: ${CLUSTER_NAME})
  API_PORT     (default: ${API_PORT})   # host port bound to k8s API:6443
  HTTP_PORT    (default: ${HTTP_PORT})  # host port bound to LB:80
  NAMESPACE    (default: ${NAMESPACE})

Examples:
  $0 create
  $0 use
  kubectl config current-context
  $0 status
  $0 delete
EOF
}

cmd="${1:-}"
if [[ -z "$cmd" ]]; then
  usage
  exit 2
fi

case "$cmd" in
  create)
    if is_staging_context "$current_ctx"; then
      echo "Refusing create while current context looks like staging/prod: '$current_ctx'"
      echo "Switch context first (or set a non-staging current context), then rerun."
      exit 1
    fi
    if k3d cluster list | awk '{print $1}' | rg -qx "${CLUSTER_NAME}"; then
      echo "Cluster '${CLUSTER_NAME}' already exists."
    else
      echo "Creating k3d cluster '${CLUSTER_NAME}'..."
      k3d cluster create "${CLUSTER_NAME}" \
        --servers 1 \
        --agents 1 \
        --api-port "${API_PORT}" \
        --port "${HTTP_PORT}:80@loadbalancer" \
        --kubeconfig-switch-context
    fi
    echo "Using context: ${KUBECONTEXT}"
    kubectl config use-context "${KUBECONTEXT}" >/dev/null
    kubectl get nodes -o wide
    ;;

  delete)
    if [[ "$current_ctx" == "$KUBECONTEXT" ]]; then
      echo "Current context is '${KUBECONTEXT}'. Deleting cluster."
    else
      echo "Deleting cluster '${CLUSTER_NAME}' (current context: '${current_ctx:-<none>}')."
    fi
    k3d cluster delete "${CLUSTER_NAME}"
    ;;

  use)
    kubectl config use-context "${KUBECONTEXT}" >/dev/null
    echo "Switched to ${KUBECONTEXT}"
    kubectl get nodes -o wide
    ;;

  status)
    echo "Current context: ${current_ctx:-<none>}"
    echo "Expected dev context: ${KUBECONTEXT}"
    echo ""
    echo "k3d clusters:"
    k3d cluster list || true
    echo ""
    if [[ "$current_ctx" == "$KUBECONTEXT" ]]; then
      echo "Dev cluster namespace check (${NAMESPACE}):"
      kubectl get ns "${NAMESPACE}" >/dev/null 2>&1 && echo "namespace exists" || echo "namespace missing"
      kubectl -n "${NAMESPACE}" get pods 2>/dev/null || true
    fi
    ;;

  *)
    usage
    exit 2
    ;;
esac
