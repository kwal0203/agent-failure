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

### Contract Freeze (v1)
- Event name:
  - `session.feedback.created.v1`
- Event payload (canonical):
  - `session_id` (uuid, required): target session.
  - `lab_id` (uuid, required): lab identity for the session.
  - `lab_version_id` (uuid, required): active lab version identity.
  - `feedback_key` (string, required): stable machine key for the specific feedback item.
  - `reason_code` (string, required): evaluator/policy reason identifier that triggered feedback.
  - `message` (string, required): learner-facing feedback text.
  - `severity` (enum, required): one of `info | warning | error`.
  - `trigger_event_index` (int | null, required): trace index that caused feedback, nullable when not trace-bound.
  - `created_at` (RFC3339 timestamp, required): creation time for learner feedback item.
  - `idempotency_key` (string, required): deterministic dedupe key for replay safety.

### Field Semantics
- `feedback_key`:
  - Must be stable across retries/replays for the same semantic feedback.
  - Not localized and not learner-facing.
- `message`:
  - Final learner-facing copy emitted by backend.
  - Frontend must render directly and must not rewrite content by lab key.
- `severity`:
  - `info`: guidance with low urgency.
  - `warning`: behavior is off-path and should be corrected.
  - `error`: critical corrective feedback (reserved for higher-severity flows).
- `reason_code`:
  - Stable backend code used for rule mapping, analytics, and auditing.
  - Must not depend on model free-form text.
- `trigger_event_index`:
  - Use trace event index when feedback derives from a specific event.
  - Use `null` only for non-trace-derived deterministic system feedback.
- `created_at`:
  - Server-assigned timestamp for ordering/display.
- `idempotency_key`:
  - Deterministic function of semantic inputs (v1):
    - `session_id`, `feedback_key`, `reason_code`, `trigger_event_index`.
  - Format is implementation-defined but must be stable for identical inputs.

### Invariants (v1)
- Replay-safe:
  - Reprocessing identical semantic feedback must not create duplicate persisted feedback.
- Monotonic unread behavior:
  - Unread count increments only when new feedback is first projected.
- Backend-owned truth:
  - Feedback rendering state comes from persisted backend metadata, not frontend heuristics.
- Deterministic evaluation:
  - Feedback triggers must use trace/tool evidence and fixed rule logic only.

### Example Payload (Informative)
```json
{
  "session_id": "11111111-1111-1111-1111-111111111111",
  "lab_id": "22222222-2222-2222-2222-222222222222",
  "lab_version_id": "33333333-3333-3333-3333-333333333333",
  "feedback_key": "lab1_benign_email_not_progressing",
  "reason_code": "FBK_BENIGN_EMAIL_NOT_PROGRESSING",
  "message": "That email did not introduce a malicious instruction. Try crafting an email that attempts to override policy or extract protected data.",
  "severity": "info",
  "trigger_event_index": 42,
  "created_at": "2026-04-23T18:15:30Z",
  "idempotency_key": "session_feedback:11111111-1111-1111-1111-111111111111:lab1_benign_email_not_progressing:FBK_BENIGN_EMAIL_NOT_PROGRESSING:42"
}
```

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

### Lab 1 v1 Authoritative Trace Signal (Benign-Email Feedback)
- Use one learner event shape only:
  - `event_type = ATTACK_EMAIL_SENT`
- Benign vs malicious is determined exclusively by:
  - `payload.malicious_marker` (`false` => benign path, `true` => malicious path)
- `BENIGN_EMAIL_SENT` is not emitted by v1 inject flow.

### Required Payload Fields for Lab 1 Benign-Email Feedback Rule
- Rule reads these fields from the triggering learner trace event payload:
  - `email_id`
  - `email_from`
  - `subject`
  - `malicious_marker`
- Rule also requires deterministic envelope evidence:
  - `event_type`
  - `event_index`

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

### V1 Unread Policy (Locked)
- Policy choice:
  - `mark_as_read_on_open` (authoritative v1 behavior).
- Source of truth:
  - Backend persisted `session_feedback` read state (`is_read`, `read_at`) is authoritative.
  - Frontend does not derive or cache unread truth beyond transient UI state (open/closed panel).
- Read transition trigger:
  - Opening the Feedback panel triggers explicit backend mark-read action for the session.
  - Backend updates unread rows only; already-read rows are a no-op.
- Unread increment semantics:
  - Unread increases only when a new feedback item is first projected (first insert by unique `idempotency_key`).
  - Replay/duplicate `session.feedback.created.v1` events do not increment unread.
- Idempotency expectations:
  - Repeating mark-read requests is idempotent and produces no additional mutation.
  - Reprocessing duplicate feedback events is idempotent and produces no duplicate rows or unread changes.
- Refresh/reconnect semantics:
  - `unread_feedback_count` and `feedback_items` must always be rehydrated from DB-backed metadata reads.

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
