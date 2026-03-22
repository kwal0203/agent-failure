# P0 Backlog-Ready Tickets

This document refines the P0 foundation epics into backlog-ready tickets with acceptance criteria, milestone target, blockers, and initial sizing.

Sizing scale used here:

- **XS**: a few hours
- **S**: about 1 day
- **M**: 1 to 2 days
- **L**: 2 to 4 days

---

# Epic 1: Session Lifecycle and Control Plane Foundation

## Ticket: P1-E1-T7 — Implement durable idle-timeout tracking (`last_activity_at`)

**Epic:** Session Lifecycle and Control Plane Foundation
**Priority:** P1
**Estimate:** M
**Milestone Target:** Post-MVP
**Owner:** TBD
**Specs:** Session Lifecycle and State Machine Spec

**Description**
Implement durable `last_activity_at` tracking and idle-timeout enforcement for `ACTIVE`/`IDLE` sessions.
This is intentionally deferred from MVP; MVP expiry covers provisioning timeout and max-lifetime only.

**Acceptance Criteria**

- `sessions.last_activity_at` is added and persisted as UTC timestamp
- qualifying learner activity updates `last_activity_at` on write paths
- expiry worker enforces idle timeout using `last_activity_at` according to policy
- idle timeout transition path uses lifecycle transition service (no direct state edits)
- tests cover activity update and idle-timeout transition behavior
- docs record idle-time policy and event semantics

**Blockers / Dependencies**

- P0-E1-T2
- P0-E1-T6

---

# Epic 3: Live Session Streaming

## Ticket: P0-E3-T4 — Enforce one interactive turn at a time

**Epic:** Live Session Streaming
**Priority:** P0
**Estimate:** S
**Milestone Target:** Milestone 1
**Owner:** TBD
**Specs:** Session Lifecycle and State Machine Spec

**Description**
Add session-level turn locking or equivalent sequencing so only one learner turn can execute at a time.

**Acceptance Criteria**

- one session cannot process two concurrent learner turns
- a second prompt during active turn is denied explicitly
- lock or sequencing mechanism is released reliably on turn completion or terminal failure
- tests cover success path and overlapping-request rejection

**Blockers / Dependencies**

- USER\_PROMPT handling exists

---

## Ticket: P0-E3-T5 — Implement reconnect replay logic

**Epic:** Live Session Streaming
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 3
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec; Trace Event Schema and Evaluator Contract Spec

**Description**
Allow clients to reconnect to a session and replay missed learner-visible events using an acknowledged event index or equivalent replay cursor.

**Acceptance Criteria**

- reconnect request can provide last acknowledged event index or replay cursor
- missed learner-visible events are replayed in durable order where available
- replay never crosses session boundaries
- reconnect falls back cleanly when replay cannot be completed
- tests cover replay after disconnect and out-of-date replay cursor handling

**Blockers / Dependencies**

- trace persistence with ordered event indices
- session stream baseline

---

# Epic 4: Sandbox Runtime and Orchestration

# Epic 5: Agent Harness and Tool Execution

## Ticket: P0-E5-T3 — Implement allowed tool registry

**Epic:** Agent Harness and Tool Execution
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 3
**Owner:** TBD
**Specs:** TDD; Trace Event Schema and Evaluator Contract Spec

**Description**
Define the approved tool surface for V1 labs and reject unsupported tool requests.

**Acceptance Criteria**

- supported V1 lab exposes an explicit allowlist of tools
- unsupported tool request is denied rather than executed
- tool invocation path includes normalized tool name and arguments
- policy denial path emits typed denial event
- tests cover allowed tool execution and unsupported tool denial

**Blockers / Dependencies**

- supported V1 lab contract defined
- trace event envelope implemented

---

## Ticket: P0-E5-T4 — Emit runtime and tool trace events

**Epic:** Agent Harness and Tool Execution
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 3
**Owner:** TBD
**Specs:** Trace Event Schema and Evaluator Contract Spec

**Description**
Emit structured events for model requests, model output completion, tool calls, tool results, and runtime failures.

**Acceptance Criteria**

- harness emits typed events conforming to trace envelope
- events include source, event type, correlation context, and payload
- runtime/tool events are persisted durably in session order
- learner-visible projection can be derived for supported events
- tests validate event envelope and ordering behavior

**Blockers / Dependencies**

- canonical trace-event envelope exists
- Control Plane persistence path exists

---

# Suggested sequencing for immediate implementation

1. P0-E1-T1 Create session lifecycle schema COMPLETE (baseline)
2. P0-E1-T2 Implement lifecycle transition service COMPLETE (baseline)
3. P0-E1-T3 Implement idempotent session creation path COMPLETE (baseline, may evolve with lab/version source-of-truth refinements)
4. P0-E3-T1 Implement WebSocket session manager COMPLETE (baseline)
5. P0-E5-T1 Build Agent Harness session loop COMPLETE (baseline)
6. P0-E5-T2 Integrate model gateway provider COMPLETE (baseline)
7. P0-E3-T2 Implement USER\_PROMPT handling COMPLETE (baseline)
8. P0-E3-T3 Emit typed stream messages COMPLETE (baseline)
9. P0-E1-T4 Implement session metadata endpoint COMPLETE (baseline)
10. P0-E4-T1 / P0-E4-T2 / P0-E4-T3 to move from local path to staging runtimes COMPLETE (staging-equivalent baseline, with documented follow-on hardening/atomicity/readiness work)

# Suggested next refinement

After these P0 tickets, the next best refinement pass is:

- Epic 6 Trace Pipeline and Replay
- Epic 8 Authentication and Authorization
- Epic 9 Quota and Abuse Controls

Those are the next most important tickets before public beta.

---
