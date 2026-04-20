# Hints Refactor Tickets (Backend-Persisted, Long-Term Architecture)

## Goal
Replace frontend-timer hints with backend-persisted, idempotent, lab-versioned hint progression so hints survive refresh/reconnect and avoid duplicate timeline events.

## Non-Goals
- No temporary dual-state hacks in production path.
- No frontend-owned unlock scheduling once migration is complete.

## Ticket 1: Data Model - Hint Template + Session Hint Tables
### Scope
- Add persistent schema for lab hint templates and session hint state.

### Deliverables
- `lab_hint_templates` table (versioned by `lab_version_id`):
  - `id` (UUID PK)
  - `lab_version_id` (UUID, indexed)
  - `hint_key` (string, stable ID, e.g. `hint_1`)
  - `text` (string/text)
  - `offset_seconds` (int, non-negative)
  - `sort_order` (int, non-negative)
  - `is_active` (bool, default true)
  - constraints:
    - unique `(lab_version_id, hint_key)`
    - unique `(lab_version_id, sort_order)`
    - non-empty `hint_key` and `text`
- `session_hints` table:
  - `id` (UUID PK)
  - `session_id` (UUID, indexed)
  - `hint_key` (string)
  - `text` (string/text snapshot)
  - `sort_order` (int)
  - `unlock_at` (timestamptz)
  - `unlocked_at` (timestamptz nullable)
  - `status` (`pending` | `unlocked`)
  - `seen_at` (timestamptz nullable)
  - `updated_at` (timestamptz)
  - constraints:
    - unique `(session_id, hint_key)`
    - check `status in ('pending','unlocked')`

### Acceptance Criteria
- Alembic migration applies cleanly.
- New tables are queryable in local/staging.

---

## Ticket 2: Seed Hint Templates for Lab 1
### Scope
- Seed `lab_hint_templates` rows for the active Lab 1 version.

### Deliverables
- Migration seed inserts all Lab 1 hints in final copy order.
- Seed uses correct `lab_version_id` from existing lab/version seed chain.

### Acceptance Criteria
- Querying `lab_hint_templates` returns expected ordered hints for Lab 1.

---

## Ticket 3: Materialize Session Hints During Provisioning Success
### Scope
- On successful provisioning, copy template hints into `session_hints`.

### Deliverables
- New application port/repository methods:
  - list templates by `lab_version_id`
  - idempotent upsert of session hints by `(session_id, hint_key)`
- Materialization logic in orchestrator success path:
  - computes `unlock_at = session_activated_at + offset_seconds`
  - initializes `status='pending'`

### Acceptance Criteria
- New sessions receive full hint set in `session_hints` exactly once.
- Reprocessing does not duplicate rows (idempotent).

---

## Ticket 4: Hint Unlock Projector/Worker + Outbox Event
### Scope
- Unlock pending hints when due, persist state, emit domain event.

### Deliverables
- Worker loop (or existing worker extension) that:
  - claims due pending hints (`unlock_at <= now()`)
  - transitions to `unlocked` with `unlocked_at=now()`
  - emits outbox event `session.hint.unlocked.v1`
- Event payload schema (typed):
  - `session_id`
  - `hint_key`
  - `text`
  - `sort_order`
  - `unlocked_at`
  - `idempotency_key`

### Acceptance Criteria
- Due hints unlock reliably in staging.
- Duplicate claims are safely ignored by idempotency.

---

## Ticket 5: Control Plane API - Expose Hints in Session Metadata
### Scope
- Include hints in metadata endpoint so UI can render persisted state.

### Deliverables
- Extend repository/query DTOs for session metadata with `hints`:
  - `hint_key`
  - `text`
  - `sort_order`
  - `status`
  - `unlock_at`
  - `unlocked_at`
  - `seen_at`
- Sort unlocked hints oldest-first for UI consumption.
- Add derived `unread_hint_count` (if using `seen_at`).

### Acceptance Criteria
- `GET /sessions/{id}` returns stable hint state across refresh.

---

## Ticket 6: API Endpoint - Mark Hints Seen
### Scope
- Backend endpoint to clear unread badge semantics.

### Deliverables
- Add endpoint: `POST /api/v1/sessions/{id}/hints/mark-seen`
- Behavior:
  - marks all unlocked unseen hints with `seen_at=now()`
  - owner/admin auth consistent with metadata rules

### Acceptance Criteria
- Unread count drops to 0 after call.
- Idempotent on repeated calls.

---

## Ticket 7: Frontend - Replace Timer-Based Hints with Backend State
### Scope
- Remove frontend unlock scheduler and source hints from metadata/events.

### Deliverables
- Delete/retire timer logic in `useHintsState`.
- New hook (`useSessionHints`) consumes metadata hint payload (+ optional stream events).
- Hints chip behavior:
  - count from unlocked hint list
  - highlight from `unread_hint_count > 0`
  - clicking chip triggers `mark-seen` endpoint
- Timeline behavior:
  - no duplicate hint unlock entries on refresh/reconnect
  - if unlock event is streamed, dedupe by stable event ID

### Acceptance Criteria
- Refreshing browser preserves hint progression and count.
- Reconnect does not replay duplicate hint timeline cards.

---

## Ticket 8: Observability + Guardrails
### Scope
- Add operational visibility and failure diagnostics.

### Deliverables
- Structured logs for:
  - template materialization count
  - due hints claimed/unlocked
  - unlock dedupe count
- Metrics counters/gauges (if metrics infra exists):
  - `hints_unlocked_total`
  - `hints_unlock_deduped_total`
  - `pending_hints_due_total`

### Acceptance Criteria
- Can diagnose unlock lag/duplication from logs/metrics in staging.

---

## Ticket 9: Tests (Unit + Integration)
### Scope
- Ensure behavior correctness and idempotency.

### Deliverables
- Unit tests:
  - template materialization idempotency
  - due-hint unlock transition
  - mark-seen semantics
- Integration tests:
  - metadata returns persisted hints after refresh
  - no duplicate hint rows/events on retries
  - frontend-visible unread count behavior

### Acceptance Criteria
- New tests pass in CI and protect against regression.

---

## Ticket 10: Cleanup and Removal of Legacy Hint Path
### Scope
- Remove obsolete frontend scheduler and dead code paths.

### Deliverables
- Remove legacy constants/scheduling refs tied to FE timers.
- Remove fallback branches no longer needed.
- Update docs with new source-of-truth architecture.

### Acceptance Criteria
- No frontend timer-based hint unlock code remains.
- Hint behavior is fully backend-driven and deterministic.

---

## Execution Notes
- Prefer additive rollout:
  1. schema + materialization
  2. unlock worker
  3. metadata/mark-seen API
  4. frontend switch
  5. cleanup
- Keep contracts typed end-to-end (repository row -> DTO -> API model -> frontend type).
- Use idempotency keys for all unlock/event projections.
