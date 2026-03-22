# P1 Backlog-Ready Tickets

This document refines the P1 product-viability epics into backlog-ready tickets with acceptance criteria, milestone target, blockers, and initial sizing.

Sizing scale used here:

- **XS**: a few hours
- **S**: about 1 day
- **M**: 1 to 2 days
- **L**: 2 to 4 days

---

# Epic 2: Learner UI Vertical Slice

## Ticket: P1-E2-T1 — Build demo app shell (auth deferred)

**Epic:** Learner UI Vertical Slice
**Priority:** P1
**Estimate:** M
**Milestone Target:** P1 Sprint 1
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec

**Description**
Create the learner-facing application shell for demo usage with session-aware navigation and no login gate.

**Acceptance Criteria**

- app shell loads without authentication dependency in local/staging demo environments
- shell includes baseline navigation for labs/sessions/history
- demo mode landing path routes directly into learner workflow
- shell state/bootstrap data is available to child pages
- frontend tests cover core routing and shell rendering paths

**Blockers / Dependencies**

- P0-E3-T1
- P0-E1-T4

---

## Ticket: P1-E2-T2 — Build lab catalog page

**Epic:** Learner UI Vertical Slice
**Priority:** P1
**Estimate:** M
**Milestone Target:** P1 Sprint 1
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec

**Description**
Implement a learner-visible lab catalog that shows launchable labs and basic capability metadata.

**Acceptance Criteria**

- lab catalog page renders list of launchable labs
- each lab row/card includes name, summary, and key metadata
- empty/error/loading states are handled explicitly
- launch action routes learner into session flow where applicable
- frontend tests cover populated and empty states

**Blockers / Dependencies**

- lab listing API or stubbed provider path
- P1-E2-T1

---

## Ticket: P1-E2-T7 — Build history view

**Epic:** Learner UI Vertical Slice
**Priority:** P1
**Estimate:** S
**Milestone Target:** P1 Sprint 1
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec

**Description**
Render learner-visible historical messages and feedback in session context.

**Acceptance Criteria**

- session page shows historical learner-visible events/messages
- ordering is stable and deterministic
- empty history state is clear and non-error
- rendering differentiates learner vs assistant/system roles where applicable
- tests cover history rendering and empty-history behavior

**Blockers / Dependencies**

- session history retrieval endpoint available

---

## Ticket: P1-E2-T8 — Build trace viewer

**Epic:** Learner UI Vertical Slice
**Priority:** P1
**Estimate:** M
**Milestone Target:** P1 Sprint 2
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec; API and WebSocket Contract Spec

**Description**
Build a learner trace viewer with pagination/cursor support and basic event-family presentation.

**Acceptance Criteria**

- trace panel renders ordered learner-visible trace events
- pagination/cursor controls load next/previous sets deterministically
- trace event rows show event type, timestamp, and summary payload
- malformed/unknown event shapes degrade gracefully
- tests cover cursor pagination and rendering

**Blockers / Dependencies**

- P1-E6-T1
- P1-E6-T6

---

# Epic 6: Trace Pipeline and Replay

## Ticket: P1-E6-T1 — Implement canonical trace-event envelope

**Epic:** Trace Pipeline and Replay
**Priority:** P1
**Estimate:** M
**Milestone Target:** P1 Sprint 1
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Define and enforce the canonical event envelope for all emitted trace families.

**Acceptance Criteria**

- shared trace envelope model exists with required fields/versioning
- lifecycle, learner, runtime, and tool events conform to envelope
- invalid envelope writes are rejected with typed validation error
- unit tests validate required/optional field behavior

**Blockers / Dependencies**

- P0-E5-T4 baseline event emission path

---

## Ticket: P1-E6-T2 — Assign session-scoped event ordering

**Epic:** Trace Pipeline and Replay
**Priority:** P1
**Estimate:** M
**Milestone Target:** P1 Sprint 1
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Guarantee monotonically increasing `event_index` per session for replay correctness.

**Acceptance Criteria**

- each persisted trace event has session-scoped monotonic index
- concurrent writes do not produce duplicate or out-of-order indices
- ordering guarantees are documented
- tests cover concurrency and ordering edge cases

**Blockers / Dependencies**

- P1-E6-T1

---

## Ticket: P1-E6-T3 — Persist lifecycle and learner events

**Epic:** Trace Pipeline and Replay
**Priority:** P1
**Estimate:** M
**Milestone Target:** P1 Sprint 1
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Persist lifecycle and learner-originated events through a shared durable trace path.

**Acceptance Criteria**

- lifecycle transition events are persisted in canonical envelope
- learner-originated events are persisted in canonical envelope
- durable writes include correlation/session context
- tests cover successful writes and validation failures

**Blockers / Dependencies**

- P1-E6-T1
- P1-E6-T2

---

## Ticket: P1-E6-T4 — Persist runtime and tool events

**Epic:** Trace Pipeline and Replay
**Priority:** P1
**Estimate:** M
**Milestone Target:** P1 Sprint 1
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Persist runtime/tool/model-related events with source attribution and envelope conformance.

**Acceptance Criteria**

- runtime/tool/model event families are persisted durably
- events include source attribution and correlation context
- unsupported event families are rejected explicitly
- tests cover event-family persistence and ordering integration

**Blockers / Dependencies**

- P0-E5-T4
- P1-E6-T1
- P1-E6-T2

---

## Ticket: P1-E6-T5 — Implement learner-visible event filtering

**Epic:** Trace Pipeline and Replay
**Priority:** P1
**Estimate:** S
**Milestone Target:** P1 Sprint 2
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Define/implement trace visibility projection for learner-safe event retrieval in demo mode (authz deferred).

**Acceptance Criteria**

- learner-visible projection excludes internal-only events using server-side allowlist rules
- projection rules are centralized, testable, and independent of auth identity
- retrieval endpoints use projection consistently
- tests cover visibility allow/deny examples

**Blockers / Dependencies**

- P1-E6-T1
- demo visibility allowlist rules (documented)

---

## Ticket: P1-E6-T6 — Implement replay cursor/pagination logic

**Epic:** Trace Pipeline and Replay
**Priority:** P1
**Estimate:** M
**Milestone Target:** P1 Sprint 2
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec; Trace Event Schema and Evaluator Contract Spec

**Description**
Support stable replay and retrieval semantics using cursor/index pagination.

**Acceptance Criteria**

- retrieval endpoint accepts cursor/index parameters
- pagination returns stable windows with deterministic ordering
- reconnect replay can request events after last acknowledged index
- tests cover cursor drift, stale cursor, and boundary conditions

**Blockers / Dependencies**

- P1-E6-T2
- P1-E6-T5
- P0-E3-T5

---

## Ticket: P1-E6-T7 — Add trace schema validation tests

**Epic:** Trace Pipeline and Replay
**Priority:** P1
**Estimate:** S
**Milestone Target:** P1 Sprint 2
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Add contract tests validating envelope and event-family schema conformance.

**Acceptance Criteria**

- positive fixture tests for supported event families
- negative fixture tests for malformed/invalid event shapes
- validation suite runs in CI path

**Blockers / Dependencies**

- P1-E6-T1

---

# Epic 7: Evaluator and Feedback Pipeline

## Ticket: P1-E7-T1 — Define evaluator worker entrypoint

**Epic:** Evaluator and Feedback Pipeline
**Priority:** P1
**Estimate:** M
**Milestone Target:** P1 Sprint 2
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Implement evaluator worker entrypoint that processes committed trace windows for one session/lab version.

**Acceptance Criteria**

- evaluator worker consumes committed trace events for one session scope
- evaluator run uses explicit lab/version context
- evaluator logs include deterministic correlation fields
- tests cover worker invocation and no-op behavior

**Blockers / Dependencies**

- P1-E6-T3
- P1-E6-T4

---

## Ticket: P1-E7-T2 — Implement evaluator idempotency keys

**Epic:** Evaluator and Feedback Pipeline
**Priority:** P1
**Estimate:** S
**Milestone Target:** P1 Sprint 2
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Prevent duplicate evaluator outputs for repeated runs over same triggering context.

**Acceptance Criteria**

- evaluator output writes are idempotent by operation key
- repeated evaluation of same input does not duplicate output rows/events
- tests cover replay/retry idempotency behavior

**Blockers / Dependencies**

- P1-E7-T1

---

## Ticket: P1-E7-T3 — Implement initial constraint bundle for V1 labs

**Epic:** Evaluator and Feedback Pipeline
**Priority:** P1
**Estimate:** M
**Milestone Target:** P1 Sprint 2
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Implement the first constraint/signal ruleset for supported V1 labs.

**Acceptance Criteria**

- evaluator includes initial V1 lab constraints/signals
- constraints map to deterministic inputs and outputs
- unsupported labs are handled explicitly
- tests cover at least one pass and one fail path per initial rule family

**Blockers / Dependencies**

- P1-E7-T1

---

## Ticket: P1-E7-T4 — Persist evaluation outputs

**Epic:** Evaluator and Feedback Pipeline
**Priority:** P1
**Estimate:** M
**Milestone Target:** P1 Sprint 2
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Persist typed evaluator outcomes and payloads in durable storage.

**Acceptance Criteria**

- evaluator output store persists result type, signal/constraint ID, triggering refs, level, payload
- persisted outputs include session and lab-version context
- tests cover write/read and schema validation behavior

**Blockers / Dependencies**

- P1-E7-T2
- P1-E7-T3

---

## Ticket: P1-E7-T5 — Publish learner-visible feedback events

**Epic:** Evaluator and Feedback Pipeline
**Priority:** P1
**Estimate:** M
**Milestone Target:** P1 Sprint 3
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec; Trace Event Schema and Evaluator Contract Spec

**Description**
Project eligible evaluator outputs into learner-visible feedback stream/history surfaces.

**Acceptance Criteria**

- learner-visible evaluator feedback is emitted as typed events/messages
- history and live stream projections are consistent
- internal-only evaluator outputs are not leaked to learners
- tests cover projection and visibility rules

**Blockers / Dependencies**

- P1-E6-T5
- P1-E7-T4

---

## Ticket: P1-E7-T6 — Support terminal-outcome handoff

**Epic:** Evaluator and Feedback Pipeline
**Priority:** P1
**Estimate:** M
**Milestone Target:** P1 Sprint 3
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec; Session Lifecycle and State Machine Spec

**Description**
Allow evaluator-detected terminal outcomes to hand off into control-plane lifecycle handling.

**Acceptance Criteria**

- evaluator terminal-outcome signals can trigger control-plane terminal handling path
- handoff path is idempotent and auditable
- lifecycle transitions still go through canonical transition service
- tests cover success and duplicate-handoff behavior

**Blockers / Dependencies**

- P1-E7-T4
- P0-E1-T2

---

## Ticket: P1-E7-T7 — Add evaluator correctness tests

**Epic:** Evaluator and Feedback Pipeline
**Priority:** P1
**Estimate:** S
**Milestone Target:** P1 Sprint 3
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Add correctness suite validating evaluator input bounds, lab/version binding, and committed-event usage.

**Acceptance Criteria**

- evaluator tests verify committed-events-only behavior
- tests verify correct lab-version binding behavior
- regression fixtures included for key constraint families

**Blockers / Dependencies**

- P1-E7-T1
- P1-E7-T3

---

# Suggested sequencing for P1 implementation (demo-first, auth deferred)

1. P1-E2-T1 Build demo app shell (auth deferred)
2. P1-E2-T2 Build lab catalog page
3. P1-E2-T7 Build history view
4. P1-E6-T1 Implement canonical trace-event envelope
5. P1-E6-T2 Assign session-scoped event ordering
6. P1-E6-T3 / P1-E6-T4 Persist trace event families
7. P1-E6-T5 / P1-E6-T6 Implement learner-visible retrieval + replay
8. P1-E2-T8 Build trace UI surface
9. P1-E7-T1..T4 Build evaluator baseline and persistence
10. P1-E7-T5..T7 Publish feedback + terminal handoff + correctness suite

# Explicitly deferred from P1 demo scope

- Full authentication and role-based authorization enforcement in UI routing
- Production-grade identity/bootstrap flows
- These are intentionally moved to a follow-on hardening/security track after demo viability

# Deferred Auth Follow-Up Ticket Seed List

Use these as the starting point for the post-demo hardening/security sprint.

## Ticket Seed: P2-E2-T10 — Implement authenticated shell route guards

- Scope: enforce authenticated/unauthenticated route boundaries in UI
- Acceptance seed:
- protected learner routes require authenticated identity
- unauthenticated users are redirected to login/bootstrap flow
- route-guard behavior is covered by frontend tests

## Ticket Seed: P2-E2-T11 — Implement role-based UI authorization

- Scope: enforce learner/admin route and action-level authorization in UI
- Acceptance seed:
- learner cannot access admin-only routes/actions
- admin routes are conditionally visible and enforced
- denied paths show explicit, user-safe messaging

## Ticket Seed: P2-E6-T8 — Bind learner-visible projection to identity claims

- Scope: evolve demo visibility allowlist into identity-aware projection rules
- Acceptance seed:
- learner-visible trace/event filtering uses identity + role claims
- projection policy is centralized and auditable
- tests cover identity-based allow/deny behavior

## Ticket Seed: P2-E0-T1 — Production auth bootstrap and token lifecycle

- Scope: production-grade auth bootstrap, token refresh, and session expiry handling
- Acceptance seed:
- app bootstrap obtains and validates identity context
- token refresh/expiry paths are handled without broken UX
- backend/frontend logs include correlation for auth failures

## Ticket Seed: P2-E0-T2 — Authorization policy conformance tests

- Scope: add integration and contract tests for authn/authz policy enforcement
- Acceptance seed:
- end-to-end tests verify route and API authorization gates
- policy regressions fail CI with clear diagnostics
- staging validation checklist includes authn/authz assertions
