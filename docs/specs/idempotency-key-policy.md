# Idempotency Key Policy

## Purpose

Define a stable, replay-safe convention for idempotency keys across `control_plane`, `evaluator`, and shared `contracts`.

## Canonical Format

Keys are lowercase, colon-delimited, deterministic strings.

General pattern:

`<domain>[:vN]:<scope identifiers>:<semantic discriminators>`

Rules:
- Use `:` as the only segment separator.
- Normalize free-text inputs with `strip().lower()`.
- Preserve UUID canonical string form.
- Use explicit sentinels for missing values (for example, `"none"`), never empty segments.
- Include version segment (`vN`) only when a format has explicit versioning requirements.
- Treat key format as append-only; add `:v2` builder for breaking changes.

## Domain Ownership

Single source of truth per domain:
- `apps/control_plane/src/application/session_stream/idempotency.py`
  - `build_turn_idempotency_key`
- `apps/control_plane/src/application/session_lifecycle/idempotency.py`
  - `build_stop_session_transition_idempotency_key`
- `apps/control_plane/src/application/orchestrator/idempotency.py`
  - `build_provision_request_idempotency_key`
  - `build_provisioning_succeeded_transition_idempotency_key`
  - `build_provisioning_failed_transition_idempotency_key`
  - `build_reconcile_missing_runtime_transition_idempotency_key`
  - `build_reconcile_failed_runtime_transition_idempotency_key`
  - `build_expired_provisioning_transition_idempotency_key`
  - `build_expired_session_transition_idempotency_key`
- `apps/control_plane/src/application/session_email/idempotency.py`
  - `build_malicious_email_objective_idempotency_key`
- `apps/control_plane/src/application/session_hints/idempotency.py`
  - `build_hint_unlock_idempotency_key`
- `apps/evaluator/src/application/idempotency.py`
  - `build_objective_event_idempotency_key`
  - `build_feedback_event_idempotency_key`
  - `build_result_idempotency_key`
- `apps/contracts/src/idempotency.py`
  - `build_session_completed_event_idempotency_key`

Do not hand-build key strings in services/routes/workers when a builder exists.

## Stability Requirements

- Same semantic operation and same normalized inputs must always produce the same key.
- Input changes that are semantically meaningful to dedupe must change the key.
- Builders must be pure functions (no time/randomness).

## Drift Prevention

Each builder must have focused unit tests that verify:
- exact string format (prefix and segment order),
- normalization behavior,
- sentinel behavior for nullable fields,
- deterministic output for repeated calls.
