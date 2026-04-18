# Event Contract: `session.objective.completed.v1`

## Purpose
Define the cross-app contract for objective completion updates:
- evaluator emits objective completion events
- control-plane consumes and projects to `session_objectives`

This event contract replaces direct evaluator writes into control-plane objective state.

## Event Type
`session.objective.completed.v1`

## Producer
- `apps/evaluator`

## Consumer
- `apps/control_plane`

## Payload Schema
Required fields:
- `session_id: UUID`
- `lab_id: UUID`
- `lab_version_id: UUID`
- `objective_key: str`
- `reason_code: str`
- `trigger_event_index: int`
- `occurred_at: datetime (UTC)`
- `idempotency_key: str`

Optional fields:
- `source: str` (default: `evaluator`)
- `evaluator_version: int`

## Idempotency Key
Format:
- `objective:{session_id}:{objective_key}:{trigger_event_index}`

Rules:
- `objective_key` must be normalized lowercase snake_case before key construction.
- `trigger_event_index` must be the specific event index that triggered completion.
- Same semantic completion event must produce the same idempotency key.

## Projector Semantics (Control-Plane)
On consume of `session.objective.completed.v1`:
1. Find row in `session_objectives` by `(session_id, objective_key)`.
2. If row state is `pending`, set:
   - `status = complete`
   - `completed_at = occurred_at` (or now if absent)
   - `updated_at = now`
3. If row is already `complete`, no-op.
4. Never regress objective state from `complete` back to `pending`.

## Mapping Ownership
- Finding/reason -> objective mapping is owned by evaluator rules logic.
- If a finding has no mapped objective, evaluator must emit no objective-completed event.

## Error Handling Expectations
- Invalid payload shape: reject and mark terminal failure with explicit error reason.
- Unknown `objective_key` for a session: safe no-op + warning log.
- Duplicate events (same idempotency key): no duplicate side effects.

## Compatibility
- Versioned contract: future breaking changes must use a new event name/version (e.g. `.v2`).
- Non-breaking additive fields may be introduced as optional.
