#!/usr/bin/env bash
set -euo pipefail

# Non-destructive Kubernetes deployment verification helper.
# Checks:
# 1) context sanity
# 2) Flux kustomization readiness (if flux CLI exists)
# 3) rollout status of core deployments
# 4) control-plane /healthz
# 5) optional smoke roundtrip against API

NS="${NS:-runtime-pool}"
FLUX_NS="${FLUX_NS:-flux-system}"
KUSTOMIZATION_NAME="${KUSTOMIZATION_NAME:-flux-system}"
API_BASE="${API_BASE:-http://127.0.0.1:30080}"
ROLLOUT_TIMEOUT="${ROLLOUT_TIMEOUT:-180s}"
RUN_SMOKE="${RUN_SMOKE:-0}"
SMOKE_PODS="${SMOKE_PODS:-1}"
SMOKE_TIMES="${SMOKE_TIMES:-2}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 2
  }
}

need kubectl
need curl

ctx="$(kubectl config current-context 2>/dev/null || true)"
if [[ -z "$ctx" ]]; then
  echo "[FAIL] no active kubectl context"
  exit 1
fi

echo "Context: $ctx"
if [[ "$ctx" == "default" || "$ctx" == *"dev"* || "$ctx" == *"local"* ]]; then
  echo "[WARN] current context looks like local dev. You probably want the remote staging context."
fi

echo ""
echo "[1/5] Namespace and core deployments"
kubectl get ns "$NS" >/dev/null
kubectl -n "$NS" get deploy \
  control-plane \
  control-plane-provisioning-worker \
  control-plane-cleanup-worker \
  >/dev/null

echo "[OK] required deployments found"

echo ""
echo "[2/5] Flux readiness (optional)"
if command -v flux >/dev/null 2>&1; then
  flux get kustomization "$KUSTOMIZATION_NAME" -n "$FLUX_NS"
  ready="$(flux get kustomization "$KUSTOMIZATION_NAME" -n "$FLUX_NS" --no-header 2>/dev/null | awk '{print $4}')"
  if [[ "$ready" != "True" ]]; then
    echo "[FAIL] flux kustomization not ready"
    exit 1
  fi
  echo "[OK] flux kustomization ready"
else
  echo "[WARN] flux CLI not installed; skipping flux check"
fi

echo ""
echo "[3/5] Rollout status"
for d in \
  control-plane \
  control-plane-provisioning-worker \
  control-plane-cleanup-worker; do
  echo "- checking deployment/$d"
  kubectl -n "$NS" rollout status "deploy/$d" --timeout="$ROLLOUT_TIMEOUT" >/dev/null
  echo "  [OK] deployment/$d rolled out"
done

echo ""
echo "[4/5] Control-plane health"
health_code="$(curl -sS -o /tmp/k8s_healthz.out -w '%{http_code}' "$API_BASE/healthz" || true)"
if [[ "$health_code" != "200" ]]; then
  echo "[FAIL] health check failed: $API_BASE/healthz (http=$health_code)"
  if [[ -s /tmp/k8s_healthz.out ]]; then
    echo "Response:"
    cat /tmp/k8s_healthz.out
  fi
  exit 1
fi
echo "[OK] $API_BASE/healthz returned 200"

echo ""
echo "[5/5] Optional smoke"
if [[ "$RUN_SMOKE" == "1" ]]; then
  if [[ ! -x "./scripts/smoke_session_roundtrip.sh" ]]; then
    echo "[FAIL] scripts/smoke_session_roundtrip.sh not found/executable"
    exit 1
  fi
  echo "Running smoke: pods=$SMOKE_PODS times=$SMOKE_TIMES"
  API_BASE="$API_BASE" ./scripts/smoke_session_roundtrip.sh "$SMOKE_PODS" "$SMOKE_TIMES"
  echo "[OK] smoke passed"
else
  echo "[SKIP] RUN_SMOKE=0"
fi

echo ""
echo "K8s deployment verification: PASS"
