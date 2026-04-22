#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "error: kubectl not found in PATH" >&2
  exit 1
fi

manifests=(
  "deploy/k8s/staging/control-plane-deployment.yaml"
  "deploy/k8s/staging/control-plane-provisioning-worker-deployment.yaml"
  "deploy/k8s/staging/control-plane-evaluator-worker-deployment.yaml"
  "deploy/k8s/staging/control-plane-cleanup-worker-deployment.yaml"
  "deploy/k8s/staging/control-plane-session-objective-completed-worker-deployment.yaml"
  "deploy/k8s/staging/control-plane-session-hint-unlock-worker-deployment.yaml"
)

for manifest in "${manifests[@]}"; do
  echo "Applying ${manifest}"
  kubectl apply -f "${ROOT_DIR}/${manifest}"
done
