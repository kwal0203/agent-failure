# Objective Progress Event-Driven Implementation Tickets

## Goal
Replace direct evaluator-to-control-plane objective writes with a clean event-driven flow:
- evaluator emits objective-complete events
- control-plane consumes and projects into `session_objectives`
- UI reads `progress_chips` from session metadata

## Ticket 1: Define Objective Completion Event Contract
### Scope
- Define canonical event type: `session.objective.completed.v1`.
- Define payload schema and idempotency key format.
- Document finding->objective mapping ownership.

### Acceptance Criteria
- Contract documented in code/docs and referenced by both apps.
- Payload includes at least: `session_id`, `lab_id`, `lab_version_id`, `objective_key`, `reason_code`, `trigger_event_index`, `occurred_at`, `idempotency_key`.

## Ticket 2: Add Evaluator Objective Event Port + Types
### Scope
- Add evaluator app-layer port for objective completion event publishing.
- Add DTO/type definitions for objective completion publish requests.

### Acceptance Criteria
- Evaluator service code depends on evaluator-local port (no control-plane app imports).
- Type checks pass.

## Ticket 3: Implement Evaluator Outbox Publisher for Objective Events
### Scope
- Add evaluator infrastructure repo to enqueue `session.objective.completed.v1` events to outbox.
- Ensure stable idempotency key generation.

### Acceptance Criteria
- Duplicate completion attempts do not generate duplicate durable events.
- Tests cover enqueue + dedupe behavior.

## Ticket 4: Wire Evaluator Loop to Emit Objective Completion Events
### Scope
- In `evaluate_trace_window_once`, map findings to objective keys.
- Publish objective completion events through the new port.
- Keep result persistence behavior unchanged.

### Acceptance Criteria
- Objective events are emitted for mapped findings even when result insert is deduped.
- Non-mapped findings produce no objective completion event.

## Ticket 5: Add Control-Plane Consumer/Projector for Objective Completion Events
### Scope
- Add control-plane worker handler for `session.objective.completed.v1`.
- Update `session_objectives` (`pending -> complete`) idempotently.

### Acceptance Criteria
- Replayed duplicate events are no-op.
- First valid event marks objective complete and sets completion timestamp.

## Ticket 6: Integrate Projector with Existing Outbox Worker Processing
### Scope
- Wire new event type into control-plane outbox dispatch path.
- Add retry/terminal-failure handling parity with existing event consumers.

### Acceptance Criteria
- New event type is processed in normal worker cycle.
- Failures are observable and retry behavior is correct.

## Ticket 7: Keep Initialization Path on Provisioning Success
### Scope
- Ensure objective materialization on `PROVISIONING_SUCCEEDED` is active and idempotent.
- Confirm it uses `lab_objectives` templates for `session.lab_version_id`.

### Acceptance Criteria
- New active session has pending objective rows exactly once.
- Reprocessing provisioning success does not create duplicates.

## Ticket 8: End-to-End Verification + Frontend Contract Validation
### Scope
- Add/extend integration tests:
  - session activation creates pending objectives
  - evaluator emits objective completion event
  - control-plane projects completion
  - metadata endpoint returns updated `progress_chips`
- Verify refresh/reconnect preserves progress state.

### Acceptance Criteria
- End-to-end tests pass.
- `GET /api/v1/sessions/{id}` remains source of truth for progress chips.

## Suggested Execution Order
1. Ticket 1
2. Ticket 2
3. Ticket 3
4. Ticket 4
5. Ticket 5
6. Ticket 6
7. Ticket 7
8. Ticket 8
