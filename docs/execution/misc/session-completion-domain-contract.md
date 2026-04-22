# Session Completion Domain Contract (v1)

## Purpose
Define canonical session completion semantics so control-plane, evaluator, and frontend use one outcome model.

## Canonical Fields
Completion state is persisted on session metadata with the following fields:

- `completion_status`: required enum
  - `in_progress`
  - `completed_success`
  - `completed_failure`
- `completed_at`: nullable timestamp
- `completion_reason_code`: nullable string

Field expectations:

- When `completion_status = in_progress`:
  - `completed_at = null`
  - `completion_reason_code = null`
- When `completion_status in (completed_success, completed_failure)`:
  - `completed_at` is non-null
  - `completion_reason_code` may be null or populated

## Lifecycle Relationship
Two independent lifecycle domains exist for a session:

- Operational lifecycle (runtime/process state):
  - `provisioning | active | terminating | terminated`
- Completion lifecycle (outcome state):
  - `in_progress | completed_success | completed_failure`

Rules:

- Operational state does not imply completion state.
- Completion state does not imply operational state.
- Services must not infer one lifecycle from the other without explicit mapping logic.

## Transition Invariants
Completion transitions follow these invariants:

- Terminal outcome state:
  - `completed_success` and `completed_failure` are terminal.
- Monotonic transitions:
  - Allowed: `in_progress -> completed_success`
  - Allowed: `in_progress -> completed_failure`
  - Disallowed: any transition out of completed states.
- Idempotent repeated writes:
  - Re-applying the same completion transition must be a no-op.
  - Replayed events with the same deterministic idempotency key must not create additional state changes.

## Implementation Notes (v1)
- Default/backfill for existing sessions: `completion_status = in_progress`.
- `completed_at` should be set from the first accepted completion transition and remain stable afterward.
- `completion_reason_code` should represent the canonical reason used for completion (if available) and remain stable after terminal transition.
