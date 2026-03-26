# Trace MVP Contract (P1-E6-T3 / P1-E6-T4)

## Purpose
Define one shared trace foundation for lifecycle, learner, runtime, tool, and model events so evaluator and replay can consume a single durable timeline.

## Scope
- In scope: event envelope, storage shape, family/type taxonomy, validation/rejection rules, context/correlation rules.
- Out of scope for this MVP contract: advanced replay pagination semantics, authz projection, evaluator scoring logic.

## 1) MVP Envelope

### Required fields
- `event_id: UUID`
- `session_id: UUID`
- `family: str` (`lifecycle` | `learner` | `runtime` | `tool` | `model`)
- `event_type: str` (family-scoped value)
- `occurred_at: datetime (UTC)`
- `source: str` (emitter identity, e.g. `http_api`, `orchestrator_worker`, `runtime`)
- `event_index: int` (monotonic per session)
- `payload: dict[str, object]`
- `trace_version: int` (start with `1`)

### Optional fields
- `correlation_id: UUID | None`
- `request_id: UUID | None`
- `actor_user_id: UUID | None`
- `lab_id: UUID | None`
- `lab_version_id: UUID | None`

## 2) Durable Store + Write Path
- Use one shared durable table: `trace_events`.
- All supported event families write to the same table.
- Writes go through one adapter/repository API (single append path), not ad-hoc per call site.

## 3) Family/Type Taxonomy + Rejection Rules

### Families
- `lifecycle`
- `learner`
- `runtime`
- `tool`
- `model`

### Rejection behavior
- Unknown `family` -> reject with typed validation error.
- Unknown `event_type` for known family -> reject with typed validation error.
- Missing required envelope field -> reject with typed validation error.
- Invalid payload shape for declared family/type -> reject with typed validation error.

## 4) Correlation + Context Rules
- `session_id` is always required.
- `event_index` is strictly monotonic per session.
- `occurred_at` must be UTC.
- `correlation_id` should be reused for events within the same user turn.
- `request_id` should identify ingress request/message when available.
- `actor_user_id` must be set for learner-originated events when principal is known.

## 5) Ticket Phasing

### P1-E6-T3 (first)
- Persist `lifecycle` + `learner` families via shared append path.
- Include required session/correlation context.
- Add tests for successful writes and validation rejection.

### P1-E6-T4 (second)
- Extend shared append path for `runtime` + `tool` + `model` families.
- Enforce source attribution and explicit unsupported-family/type rejection.
- Add integration tests for family persistence and rejection cases.

## 6) Short-Term Pragmatism Notes
- Existing lifecycle persistence (`session_transition_events`) remains in place.
- For MVP, mirror/append lifecycle into `trace_events` for evaluator/replay input.
- Long-term, keep one canonical trace projection path and avoid divergent event semantics.
