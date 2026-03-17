#!/usr/bin/env bash
set -euo pipefail

command -v kubectl >/dev/null 2>&1 || { echo "kubectl not found"; exit 1; }

echo "[1/4] Applying namespaces..."
kubectl apply -f deploy/k8s/staging/namespaces.yaml

kubectl wait --for=create serviceaccount/default -n control-plane --timeout=60s
kubectl wait --for=create serviceaccount/default -n runtime-pool --timeout=60s

echo "[2/4] Applying control-plane config/secret..."
kubectl apply -f deploy/k8s/staging/control-plane-config.yaml

echo "[3/4] Applying runtime smoke pod..."
kubectl apply -f deploy/k8s/staging/runtime-smoke-pod.yaml

echo "[4/4] Verifying..."
kubectl get ns control-plane runtime-pool
kubectl -n runtime-pool get pod runtime-smoke

echo "Bootstrap complete."
