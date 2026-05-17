# Start/Stop Reliability Plan

## Goal
Make lab session start/stop behavior production-grade: deterministic, observable, and resilient to race conditions, transient infrastructure failures, and worker restarts.

## Success Criteria
- Start success rate >= 99.9% over 7 days (excluding intentional policy rejects).
- Stop success rate >= 99.9% over 7 days.
- P95 start time <= 20s; P99 <= 45s.
- Zero long-lived drift states (`ACTIVE` with no runtime object) beyond 2 minutes.
- All start/stop failures are explainable by structured reason codes and traceable by correlation ID.

## Current Risks (Observed)
- Runtime lifecycle relies on bare Pod + Service creation.
- Asynchronous outbox/worker flow can surface timing races as user-facing inconsistency.
- Reconciliation logic exists in code but is not a first-class production control loop.
- Prior environment-coupling bug (`APP_ENV`/runtime lock path selection) showed how config drift can impact reliability.

## Phase 0: Immediate Stabilization (1-2 PRs)
### 0.1 Environment correctness lock-in
- Keep `APP_ENV` env-specific in overlays.
- Keep provisioning worker image resolver env-aware (`production` vs `staging` paths).
- Add startup assertion/logging that selected lock/selection files exist and are environment-matching.

### 0.2 Stop-path guardrails
- Verify stop endpoint always emits structured audit fields:
  - `session_id`, `requested_by_user_id`, `requested_via`, `idempotency_key`, `correlation_id`.
- Ensure cleanup worker verification remains strict (`deleted`/`already_gone` only).

### 0.3 Fast visibility
- Add a simple admin diagnostics endpoint or script output for one session:
  - session state
  - runtime binding
  - outbox provisioning status
  - outbox cleanup status
  - transition timeline

## Phase 1: Deterministic State Enforcement (2-4 PRs)
### 1.1 Promote reconciliation to always-on production control loop
- Deploy `runtime_inspection_worker` in staging and production.
- Reconciliation policy:
  - `ACTIVE` + runtime missing => transition to `FAILED` (reason: `RUNTIME_MISSING`) or `RECOVERING` (if adding new state).
  - `PROVISIONING` beyond SLA => retry/failed with explicit reason.

### 1.2 Start readiness contract hardening
- Keep `PROVISIONING` until both are true:
  - k8s runtime object exists and Ready
  - runtime `/healthz` responds OK
- Only then mark outbox processed + transition to `ACTIVE` + write runtime binding `ready`.

### 1.3 Stop readiness contract hardening
- Do not report final stop completion until pod and service deletion are verified.
- If verification fails, requeue cleanup with capped retries + explicit retryable reason code.

## Phase 2: Runtime Lifecycle Architecture Upgrade (3-6 PRs)
### 2.1 Replace bare runtime Pod model
- Move per-session runtime lifecycle to controller-managed objects:
  - preferred: per-session `Deployment` (or `Job` if semantics fit).
- Ensure owner references and labels are deterministic and queryable.

### 2.2 Explicit operation model for frontend/API
- Start/stop endpoints return `operation_id`.
- Add operation status endpoint (`pending|running|succeeded|failed`).
- UI renders operation progress instead of optimistic assumptions.

### 2.3 Idempotent orchestration contract
- Every start/stop command keyed by deterministic idempotency key.
- Duplicate requests return current operation status, never spawn duplicate effects.

## Phase 3: Queue/Worker Reliability Hardening (2-4 PRs)
### 3.1 Outbox semantics
- Enforce at-least-once processing with dedupe-safe handlers.
- Add dead-letter handling for terminal failures.
- Add replay tooling for dead-letter events.

### 3.2 Worker runtime hardening
- Health probes for workers.
- Graceful shutdown and in-flight claim handling.
- Backoff/jitter tuning per failure reason class.

## Phase 4: Observability + SLOs (2-3 PRs)
### 4.1 Metrics
Add counters/histograms:
- `session_start_requests_total`
- `session_start_success_total`
- `session_start_failed_total{reason_code}`
- `session_start_latency_seconds`
- `session_stop_requests_total`
- `session_stop_success_total`
- `session_stop_failed_total{reason_code}`
- `session_stop_latency_seconds`
- `session_drift_detected_total`

### 4.2 Alerting
- Alert on start/stop success-rate drops.
- Alert on drift count > threshold.
- Alert on repeated retry exhaustion.

### 4.3 Correlation & tracing
- Ensure request -> outbox -> worker -> transition logs share a correlation key.
- Add one-command trace query in runbook.

## Phase 5: Verification and Chaos Testing (2-4 PRs)
### 5.1 Deterministic integration tests
- Start then verify runtime exists/ready and state == `ACTIVE`.
- Stop then verify runtime removed and state terminal.
- Repeat loops (N=20+) to catch flakiness.

### 5.2 Race tests
- Concurrent start requests with same/different idempotency keys.
- Stop during provisioning.
- Start immediately after stop.

### 5.3 Fault injection
- Simulate kubectl/API transient failures.
- Simulate pod eviction/restart during provisioning.
- Verify reconciliation correctness.

## Deployment Strategy
- Roll out each phase in staging first with load/repeat tests.
- Promote via digest PR flow after green validation.
- Use canary worker rollout where possible.
- Keep rollback criteria explicit (SLO regression threshold).

## Recommended PR Sequence (Fastest Risk Reduction)
1. Deploy runtime inspection worker + drift remediation transitions.
2. Start/stop readiness contract hardening (state transitions only on verified conditions).
3. Operation model (`operation_id`) and UI progress handling.
4. Metrics + alerts + runbook diagnostics.
5. Runtime object model migration (Pod -> Deployment/Job).

## Non-Goals (for now)
- Full custom operator build.
- Multi-cluster active-active orchestration.
- Zero-downtime live session migration between nodes.
