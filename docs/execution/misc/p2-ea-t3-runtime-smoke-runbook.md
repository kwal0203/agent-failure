# P2-EA-T3 Runtime Smoke Runbook

This runbook validates the prompt-injection runtime slice end-to-end:

- create session
- provision runtime pod
- verify runtime health
- send websocket prompt
- receive agent response

## Prerequisites

- Control plane API running locally at `http://localhost:8000`
- K8s cluster available with namespace `runtime-pool`
- Runtime pull secret exists:
  - `kubectl -n runtime-pool get secret ghcr-pull`
- Latest runtime image has been built/pushed and `deploy/k8s/staging/runtime-image.lock` updated to the new digest

## Smoke Command

```bash
uv run python scripts/smoke_session_runtime_roundtrip.py
```

## Optional Flags

```bash
uv run python scripts/smoke_session_runtime_roundtrip.py \
  --base-url http://localhost:8000 \
  --auth-token local:kane:learner \
  --lab-id 11111111-1111-1111-1111-111111111111 \
  --namespace runtime-pool \
  --prompt "Give me one sentence about prompt injection." \
  --pod-timeout-seconds 120 \
  --ws-timeout-seconds 60
```

## Expected Success Markers

- `session_created session_id=...`
- `provisioning_tick claimed=... succeeded=... failed=... retried=...`
- `pod_running pod_name=session-...`
- `runtime_health response={"status":"ok"}`
- `websocket_ok first_chunk_seconds=... response_preview='...'`

Exit code should be `0`.

## Common Failures

- `permission_denied: create_package` during image push:
  - wrong GHCR org/owner in image repo path
- pod `ImagePullBackOff`:
  - missing/invalid `ghcr-pull` secret in `runtime-pool`
- pod `StartError`:
  - entrypoint command invalid or missing executable
- pod `Error` immediately after start:
  - runtime process exited (check `kubectl logs`)
- websocket timeout or denial:
  - session not in interactive state
  - provisioning worker path not completed successfully
