# P2-W2 Runtime Gateway E2E Runbook

This runbook validates the runtime streaming path end-to-end:

- frontend websocket prompt
- control-plane runtime HTTP client
- runtime container `/runtime/v1/turns/stream`
- agent harness gateway client
- OpenRouter streaming back to UI

## Prerequisites

- Postgres running locally
- Kind cluster context healthy (for provisioning flow):
  - `kubectl cluster-info`
- Namespace exists:
  - `kubectl get ns runtime-pool || kubectl create ns runtime-pool`
- Control-plane configured with runtime client env:
  - `RUNTIME_BASE_URL=http://127.0.0.1:8001`
  - `RUNTIME_AUTH_TOKEN=dev-secret`
  - `RUNTIME_TIMEOUT_SECONDS=20`

## 1. Build Runtime Image (Repo Root)

```bash
docker build -f archive/runtimes/baseline/Dockerfile -t ghcr.io/kane/agent-failure-runtime-v1:v1-baseline-0.1.0 .
```

## 2. Run Runtime Container (Gateway Mode)

```bash
docker run --rm -p 8001:8000 \
  -e RUNTIME_SHARED_TOKEN=dev-secret \
  -e MODEL_CLIENT_MODE=gateway \
  -e PROVIDER_ENDPOINT=https://openrouter.ai/api/v1/chat/completions \
  -e OPENROUTER_API_KEY=<YOUR_KEY> \
  -e MODEL_NAME=<YOUR_MODEL> \
  -e MODEL_TIMEOUT=30 \
  ghcr.io/kane/agent-failure-runtime-v1:v1-baseline-0.1.0
```

Quick health check:

```bash
curl -sS http://127.0.0.1:8001/healthz
```

## 3. Start Control Plane

```bash
export RUNTIME_BASE_URL=http://127.0.0.1:8001
export RUNTIME_AUTH_TOKEN=dev-secret
export RUNTIME_TIMEOUT_SECONDS=20
uv run uvicorn apps.control_plane.src.interfaces.http.main:app --reload --port 8000
```

## 4. Start Provisioning Worker

```bash
uv run python -m apps.control_plane.src.interfaces.runtime.provisioning_worker
```

Expected provisioning worker marker for a successful launch tick:

- `claimed=1 succeeded=1 failed=0 retried=0`

## 5. Launch Session + Send Prompt

From frontend, create/launch a session and submit a prompt.

Expected behavior:

- Prompt accepted over websocket
- Agent text streams back to UI
- Response is model-generated (not fake template)

## 6. Confirm Model Trace Events

Check session trace endpoint for model events:

- `MODEL_TURN_STARTED`
- `MODEL_TURN_COMPLETED` (or `MODEL_TURN_FAILED`)

## Failure Checks

### A) Runtime call returns HTTP 500 in control-plane logs

Check runtime container logs:

```bash
docker logs <runtime_container_name>
```

Most common cause: missing gateway env (`PROVIDER_ENDPOINT`, `OPENROUTER_API_KEY`, `MODEL_NAME`).

### B) Provisioning fails with `K8S_APPLY_FAILED`

If payload includes `failed to download openapi` / `connection refused`, kube context is stale.

Recover:

```bash
kind delete cluster --name agent-failure-staging
kind create cluster --name agent-failure-staging
kubectl config use-context kind-agent-failure-staging
kubectl cluster-info
kubectl get ns runtime-pool || kubectl create ns runtime-pool
```

### C) Response looks fake (`I can help with that. You asked: ...`)

Runtime is in fake mode.

Set in runtime container:

- `MODEL_CLIENT_MODE=gateway`
