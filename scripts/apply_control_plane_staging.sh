#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "error: kubectl not found in PATH" >&2
  exit 1
fi

manifests=(
  "deploy/k8s/staging"
)

for manifest in "${manifests[@]}"; do
  echo "Applying kustomize ${manifest}"
  kubectl apply -k "${ROOT_DIR}/${manifest}"
done
