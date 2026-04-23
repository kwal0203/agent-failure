# Feedback System Implementation Tickets

## Goal
Ship a backend-driven learner feedback system that:
- emits deterministic feedback when learner actions do not advance objectives
- projects feedback state replay-safely in control-plane storage
- exposes feedback via session metadata
- renders feedback in UI with no lab-specific frontend branching

## Ticket 1: Freeze Feedback Domain Contract (v1)
### Scope
- Define the canonical feedback model and event contract before implementation.

### Deliverables
- Document v1 feedback fields and enums in this file (or linked lab spec):
  - `feedback_key` (stable identifier)
  - `message`
  - `severity`: `info | warning | error`
  - `reason_code`
  - `trigger_event_index` (nullable)
  - `created_at`
  - deterministic `idempotency_key`
- Define event contract target:
  - `session.feedback.created.v1`

### Acceptance Criteria
- Engineers can implement evaluator, projector, and UI without ambiguity about payload shape or semantics.

---

## Ticket 2: Add Feedback Event Contract in `apps/contracts`
### Scope
- Introduce typed, versioned contract support for feedback events.

### Deliverables
- Add `session.feedback.created.v1` event name/type literals.
- Add payload schema/model with required v1 fields:
  - `session_id`, `lab_id`, `lab_version_id`
  - `feedback_key`, `reason_code`, `message`, `severity`
  - `trigger_event_index` (nullable)
  - `occurred_at`
  - `idempotency_key`
- Include event in stream/outbox unions and validators.

### Acceptance Criteria
- Contract parsing/validation accepts valid payloads and rejects invalid shapes deterministically.

---

## Ticket 3: Add Feedback Persistence Schema + Repository Support
### Scope
- Persist feedback as backend source of truth for session metadata.

### Deliverables
- Migration for `session_feedback` (or equivalent) with fields:
  - `session_id`, `feedback_key`, `reason_code`, `message`, `severity`
  - `trigger_event_index` (nullable)
  - `created_at`
  - `idempotency_key` (unique per semantic feedback event)
  - read/unread tracking fields as needed for metadata unread counters
- Repository/model updates for create/read/update paths.
- Backfill/default strategy for existing sessions.

### Acceptance Criteria
- Feedback state persists and reloads across refresh/reconnect.

---

## Ticket 4: Add Evaluator Feedback Rules (Lab 1 v1 Slice)
### Scope
- Add deterministic, trace-driven feedback findings for non-progressing actions.

### Deliverables
- New/extended evaluator rule module for feedback reason codes.
- Initial Lab 1 rule:
  - benign injected email yields feedback finding (constraint not satisfied)
- Rule evidence uses trace events/payload only (no model assertions).

### Acceptance Criteria
- Evaluator emits feedback finding for benign email path and does not emit it for malicious path.

---

## Ticket 5: Map Feedback Findings to `session.feedback.created.v1`
### Scope
- Wire evaluator findings to feedback event emission using existing outbox pipeline.

### Deliverables
- Mapping in evaluator service from feedback reason code -> feedback payload template.
- Reuse existing outbox enqueue path (no parallel publisher stack).
- Deterministic idempotency key builder for feedback events.

### Acceptance Criteria
- Each semantic feedback trigger emits exactly one feedback event per deterministic idempotency key.

---

## Ticket 6: Add Feedback Projector Worker
### Scope
- Consume `session.feedback.created.v1` and project persisted feedback state.

### Deliverables
- Worker/service handler analogous to objective/hint workers.
- Strict payload parsing via contracts.
- Idempotent replay behavior:
  - duplicate event does not duplicate row or unread increments
- Staging manifest + runtime wiring.

### Acceptance Criteria
- Feedback projection is replay-safe and stable under duplicate processing.

---

## Ticket 7: Expose Feedback via Session Metadata API
### Scope
- Make feedback available through existing metadata channel.

### Deliverables
- Extend session metadata response with:
  - `feedback_items`
  - `unread_feedback_count`
- Direct projection from persisted feedback state (no frontend joins).
- Preserve existing metadata fields unchanged.

### Acceptance Criteria
- Frontend can render feedback entirely from metadata response.

---

## Ticket 8: Frontend Feedback UI (Metadata-Driven)
### Scope
- Render feedback using backend metadata only.

### Deliverables
- Wire `Feedback` chip unread badge/count to `unread_feedback_count`.
- Add feedback panel/modal list sourced from `feedback_items`.
- No lab/objective-key-specific UI branching.

### Acceptance Criteria
- Feedback display remains correct across refresh/reconnect and lab switches.

---

## Ticket 9: Read/Unread Behavior (v1)
### Scope
- Define and implement deterministic unread semantics.

### Deliverables
- Choose v1 policy:
  - `mark_as_read_on_open`, or
  - explicit mark-read action endpoint/event
- Implement unread update path with replay safety.
- Ensure unread increments only for newly projected feedback.

### Acceptance Criteria
- Unread counts are monotonic/accurate and do not double increment on replay.

---

## Ticket 10: End-to-End and Idempotency Coverage
### Scope
- Validate deterministic behavior across evaluator, workers, API, and UI.

### Deliverables
- Tests for:
  - benign email -> feedback event emitted once
  - malicious email -> no benign feedback
  - duplicate/replay -> no duplicate feedback state mutation
  - metadata reflects persisted feedback after refresh/reconnect
  - UI renders feedback from metadata payload
- Local runbook for manual verification.

### Acceptance Criteria
- Feedback behavior is deterministic, replay-safe, and visible end-to-end.

---

## Suggested Execution Order (Pragmatic)
1. Ticket 1
2. Ticket 2
3. Ticket 4
4. Ticket 5
5. Ticket 3
6. Ticket 6
7. Ticket 7
8. Ticket 8
9. Ticket 9
10. Ticket 10

## Notes
- Start with Lab 1 benign-email feedback as the vertical slice.
- Keep rule logic deterministic and trace-driven.
- Prefer shared infrastructure paths (outbox, workers, metadata polling) over new bespoke pipelines.
