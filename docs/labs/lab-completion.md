# Lab Completion Implementation Tickets

## Goal
Add a backend-owned, deterministic session completion system that supports:
- successful completion when required objectives are met
- future unsuccessful completion states without frontend rewrites
- replay-safe eventing and idempotent projection
- stable UI rendering from metadata

---

## Ticket 1: Define Session Completion Domain Contract
### Scope
- Establish canonical completion model and lifecycle semantics across services.

### Deliverables
- Document canonical completion fields and enums:
  - `completion_status`: `in_progress | completed_success | completed_failure`
  - `completed_at` (nullable timestamp)
  - `completion_reason_code` (nullable string)
- Clarify relationship to existing runtime/session lifecycle (`provisioning`, `active`, `terminating`, `terminated`).
- Define invariants:
  - completion is terminal for a session outcome state
  - completion transitions are monotonic and idempotent.

### Acceptance Criteria
- Engineers can implement completion behavior without interpreting ambiguous state semantics.

---

## Ticket 2: Add Persistence Schema for Completion State
### Scope
- Persist completion state in control-plane storage as backend source of truth.

### Deliverables
- Migration updates for session metadata storage to include:
  - `completion_status`
  - `completed_at`
  - `completion_reason_code`
- Repository/model updates to read/write these fields.
- Backfill/default strategy for existing rows (`in_progress`).

### Acceptance Criteria
- Session records persist and reload completion state consistently across refresh/reconnect.

---

## Ticket 3: Define Completion Event Contract
### Scope
- Introduce a dedicated completion event for decoupled projection and auditability.

### Deliverables
- New contract event (e.g. `session.completed.v1`) with payload:
  - `session_id`, `lab_id`, `lab_version_id`
  - `outcome` (`completed_success | completed_failure`)
  - `completion_reason_code`
  - `trigger_event_index` (nullable)
  - `occurred_at`
  - deterministic `idempotency_key`
- Contract + schema validation tests.

### Acceptance Criteria
- Completion event is versioned, typed, and safe for replay/dedupe.

---

## Ticket 4: Implement Completion Policy Evaluator Adapter (Success v1)
### Scope
- Build backend policy layer that decides when a session is complete.

### Deliverables
- Policy service/function that evaluates session objective state for completion.
- Initial policy for Lab 1:
  - mark `completed_success` when all required objectives are complete.
- Policy interface supports future failure modes without schema changes.

### Acceptance Criteria
- Lab 1 completion decision is deterministic and traceable to persisted objective state.

---

## Ticket 5: Emit Completion Event from Existing Objective Flow
### Scope
- Wire completion emission into current evaluator/objective pipeline.

### Deliverables
- Reuse existing outbox enqueue path (no parallel publisher stack).
- On objective completion updates, evaluate completion policy and enqueue `session.completed.v1` when terminal condition is first met.
- Deterministic idempotency key builder for completion events.

### Acceptance Criteria
- Exactly one completion event is emitted per deterministic completion trigger.

---

## Ticket 6: Add Completion Projector/Worker Handling
### Scope
- Consume completion events and project session completion state.

### Deliverables
- Worker handler for `session.completed.v1` updates session metadata fields.
- Idempotent replay behavior (duplicate event = no state mutation).
- Preserve existing objective/hint workers and ordering assumptions.

### Acceptance Criteria
- Completion state is projected once and remains stable under duplicate reprocessing.

---

## Ticket 7: Expose Completion State in Session Metadata API
### Scope
- Make completion state available to frontend via existing metadata channel.

### Deliverables
- Extend metadata DTO/response to include completion fields.
- Keep backward compatibility for clients not yet using completion state.
- Endpoint tests for response shape and field values.

### Acceptance Criteria
- Frontend can render completion status from backend metadata without custom joins.

---

## Ticket 8: Add Generic Frontend Completion Indicator
### Scope
- Render outcome UI driven solely by backend completion state.

### Deliverables
- Session UI indicator/banner/chip for:
  - `in_progress`
  - `completed_success`
  - `completed_failure` (placeholder visuals now, full UX later)
- No lab-specific branching by objective key.
- No client-side computation of completion state.

### Acceptance Criteria
- Lab 1 shows clear successful completion when backend status is `completed_success`.

---

## Ticket 9: End-to-End and Idempotency Coverage
### Scope
- Verify deterministic behavior across evaluator, workers, API, and UI.

### Deliverables
- Tests for:
  - success completion emitted once when all objectives complete
  - duplicate/replay does not duplicate completion mutation
  - metadata reflects persisted completion after refresh/reconnect
  - UI displays completion indicator from metadata response.
- Targeted integration runbook for local/manual verification.

### Acceptance Criteria
- Completion behavior is deterministic, replay-safe, and visible end-to-end.

---

## Ticket 10: Future Failure-Path Readiness (Scaffolding)
### Scope
- Prepare extension points for unsuccessful outcomes without implementing full failure UX yet.

### Deliverables
- Reason-code namespace and placeholders for future failure triggers:
  - timeout
  - manual termination before success
  - policy-defined fail condition
- Test stubs/contract guards to prevent breaking the outcome enum and API shape.

### Acceptance Criteria
- Codebase is ready to add failure completion policies in a follow-up ticket set with minimal churn.

---

## Suggested Execution Order
1. Ticket 1
2. Ticket 2
3. Ticket 3
4. Ticket 4
5. Ticket 5
6. Ticket 6
7. Ticket 7
8. Ticket 8
9. Ticket 9
10. Ticket 10
