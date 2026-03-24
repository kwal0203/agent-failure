# P2 Backlog-Ready Tickets (Thin-Slice Demo)

This document defines a focused thin-slice backlog for a real learner-facing demo.
It gathers the critical tickets from P1 and adds missing implementation tickets required
for end-to-end demo viability.

Sizing scale used here:

- **XS**: a few hours
- **S**: about 1 day
- **M**: 1 to 2 days
- **L**: 2 to 4 days

---

# Epic A: Demo API and Runtime Slice

## Ticket: P2-EA-T1 — Implement `GET /api/v1/labs` catalog endpoint

**Epic:** Demo API and Runtime Slice
**Priority:** P1
**Estimate:** M
**Milestone Target:** P2 Sprint 1
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec

**Description**
Implement the learner-visible lab catalog endpoint so the frontend can render launchable labs from backend data.

**Acceptance Criteria**

- `GET /api/v1/labs` returns typed lab catalog payload for learner role
- response includes `id`, `slug`, `name`, `summary`, and capability metadata
- non-launchable/disabled labs are excluded (or explicitly marked per policy)
- endpoint enforces authn/authz consistently with existing learner APIs
- integration tests cover success, empty catalog, and auth failure behavior

**Blockers / Dependencies**

- API/auth baseline already in place for learner endpoints

---

## Ticket: P2-EA-T2 — Wire frontend lab catalog to backend endpoint

**Epic:** Demo API and Runtime Slice
**Priority:** P1
**Estimate:** S
**Milestone Target:** P2 Sprint 1
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec

**Description**
Switch labs UI to consume `/api/v1/labs` in demo/staging and keep clear fallback behavior for local dev.

**Acceptance Criteria**

- labs page fetches from `/api/v1/labs` in API mode
- loading/error/empty/populated states remain explicit
- launch action still routes to session flow with selected `lab_id`
- frontend tests cover API-populated and API-empty behavior

**Blockers / Dependencies**

- P2-EA-T1
- P1-E2-T2 (completed baseline UI)

---

## Ticket: P2-EA-T3 — Deliver runnable prompt-injection runtime slice

**Epic:** Demo API and Runtime Slice
**Priority:** P1
**Estimate:** L
**Milestone Target:** P2 Sprint 1
**Owner:** TBD
**Specs:** Sandbox and Runtime Isolation Spec; PRD

**Description**
Provide at least one real lab runtime path (prompt injection) that can be launched and interacted with end-to-end.

**Implementation Notes**
- Runtime smoke runbook: `docs/execution/p2-ea-t3-runtime-smoke-runbook.md`

**Acceptance Criteria**

- prompt-injection lab entry is launchable from catalog
- runtime image/entrypoint is long-lived and interactive (not immediate `Completed` exit)
- provisioning path creates pod successfully in staging-like env
- websocket prompt/response loop works for launched session
- smoke test script demonstrates create -> provision -> prompt -> response for this lab

**Blockers / Dependencies**

- runtime image pipeline and pull secret baseline
- P0-E4 runtime orchestration baseline (completed)

---

## Ticket: P2-EA-T4 — Session launch/stream health hardening for demo reliability

**Epic:** Demo API and Runtime Slice
**Priority:** P1
**Estimate:** M
**Milestone Target:** P2 Sprint 1
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec

**Description**
Harden the demo path so session launch and live prompt streaming are reliable under normal retries and transient delays.

**Acceptance Criteria**

- `POST /api/v1/sessions` + provisioning path has clear error propagation to UI
- websocket turn lifecycle avoids stuck `TURN_IN_PROGRESS` states on provider failures/timeouts
- key latencies are logged (`turn_start`, `provider_start`, `first_chunk`, `turn_end`)
- runbook documents required workers/processes for demo operation

**Blockers / Dependencies**

- P0-E3 streaming baseline (completed)
- P0-E4 provisioning baseline (completed)

---

# Epic B: Trace Persistence for Evaluator Inputs

## Ticket: P1-E6-T3 — Persist lifecycle and learner events

**Epic:** Trace Pipeline and Replay
**Priority:** P1
**Estimate:** M
**Milestone Target:** P2 Sprint 1
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Persist lifecycle and learner-originated events through a shared durable trace path.

**Acceptance Criteria**

- lifecycle transition events are persisted durably
- learner-originated events are persisted durably
- writes include session/correlation context
- tests cover successful writes and validation failures

**Blockers / Dependencies**

- minimal shared trace shape documented for MVP

---

## Ticket: P1-E6-T4 — Persist runtime and tool events

**Epic:** Trace Pipeline and Replay
**Priority:** P1
**Estimate:** M
**Milestone Target:** P2 Sprint 1
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Persist runtime/tool/model-related events with source attribution so evaluator has end-to-end trace input.

**Acceptance Criteria**

- runtime/tool/model event families are persisted durably
- events include source attribution and correlation context
- unsupported families are rejected explicitly
- tests cover event-family persistence integration

**Blockers / Dependencies**

- P0-E5-T4 baseline event emission path
- P1-E6-T3

---

# Epic C: Evaluator Baseline and Feedback

## Ticket: P1-E7-T1 — Define evaluator worker entrypoint

**Epic:** Evaluator and Feedback Pipeline
**Priority:** P1
**Estimate:** M
**Milestone Target:** P2 Sprint 2
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
**Milestone Target:** P2 Sprint 2
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
**Milestone Target:** P2 Sprint 2
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Implement first-pass constraint/signal ruleset for the prompt-injection lab slice.

**Acceptance Criteria**

- evaluator includes initial V1 prompt-injection constraints/signals
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
**Milestone Target:** P2 Sprint 2
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
**Milestone Target:** P2 Sprint 2
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec; Trace Event Schema and Evaluator Contract Spec

**Description**
Project evaluator outputs into learner-visible feedback events/messages for live stream and history surfaces.

**Acceptance Criteria**

- learner-visible evaluator feedback is emitted as typed events/messages
- internal-only evaluator outputs are not leaked to learners
- live stream and stored retrieval are consistent for learner-visible feedback
- tests cover projection and visibility rules

**Blockers / Dependencies**

- P1-E7-T4

---

# Epic D: Minimal Learner Feedback Surface

## Ticket: P2-ED-T1 — Add minimal feedback panel to session UI

**Epic:** Minimal Learner Feedback Surface
**Priority:** P1
**Estimate:** S
**Milestone Target:** P2 Sprint 2
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec

**Description**
Render evaluator feedback in the learner UI in a minimal, demo-ready format (for example pass/fail + reason).

**Acceptance Criteria**

- session UI shows learner-visible evaluator feedback entries
- presentation is simple and deterministic (status + short reason)
- empty feedback state is explicit and non-error
- frontend tests cover feedback rendering and no-feedback state

**Blockers / Dependencies**

- P1-E7-T5

---

# Suggested sequencing for P2 thin-slice implementation

1. P2-EA-T1 Implement `GET /api/v1/labs`
2. P2-EA-T2 Wire frontend catalog to `/api/v1/labs`
3. P2-EA-T3 Deliver runnable prompt-injection runtime slice
4. P2-EA-T4 Harden session launch/stream reliability
5. P1-E6-T3 / P1-E6-T4 Persist evaluator-required trace families
6. P1-E7-T1..T4 Build evaluator baseline and persistence
7. P1-E7-T5 Publish learner-visible feedback events
8. P2-ED-T1 Render minimal learner feedback panel in UI

# Explicitly deferred from this thin-slice

- P1-E6-T1 full canonical envelope rollout across all producers
- P1-E6-T2 global session-scoped event ordering guarantees
- Full replay/history cursor semantics beyond demo-critical needs
- Full authn/authz hardening track
