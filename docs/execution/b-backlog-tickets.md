# P0 Backlog-Ready Tickets

This document refines the P0 foundation epics into backlog-ready tickets with acceptance criteria, milestone target, blockers, and initial sizing.

Sizing scale used here:

- **XS**: a few hours
- **S**: about 1 day
- **M**: 1 to 2 days
- **L**: 2 to 4 days

---

# Epic 1: Session Lifecycle and Control Plane Foundation

## Ticket: P0-E1-T1 — Create session lifecycle schema

**Epic:** Session Lifecycle and Control Plane Foundation
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 1
**Owner:** TBD
**Specs:** Session Lifecycle and State Machine Spec; TDD

**Description**
Add or update the durable session schema so the system can represent lifecycle state, lab-version binding, idempotency, runtime identity, and core timestamps required by the state machine.

**Acceptance Criteria**

- session persistence includes durable lifecycle state
- session persistence includes lab id and lab version id
- session persistence includes idempotency key with uniqueness enforcement
- session persistence includes runtime identity field(s) suitable for orchestration lookup
- session persistence includes created/started/ended/updated timestamps
- schema supports terminal states defined in the lifecycle spec
- migration runs successfully in local development

**Blockers / Dependencies**

- session lifecycle spec approved
- database migration path available

---

## Ticket: P0-E1-T2 — Implement lifecycle transition service

**Epic:** Session Lifecycle and Control Plane Foundation
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 1
**Owner:** TBD
**Specs:** Session Lifecycle and State Machine Spec

**Description**
Create a backend service/module that owns lifecycle transitions and rejects invalid state changes.

**Acceptance Criteria**

- there is one shared transition path used by session lifecycle writes
- allowed transitions succeed when preconditions are met
- disallowed transitions are rejected with typed errors
- terminal states reject further lifecycle regression
- transition writes persist previous state, next state, reason code, and timestamp where required
- unit tests cover all allowed and disallowed durable transitions

**Blockers / Dependencies**

- P0-E1-T1

---

## Ticket: P0-E1-T3 — Implement idempotent session creation path

**Epic:** Session Lifecycle and Control Plane Foundation
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 1
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec; Session Lifecycle and State Machine Spec

**Description**
Build session creation logic that accepts an idempotency key, creates a new session in PROVISIONING, and prevents duplicate launches.

**Acceptance Criteria**

- POST session creation accepts idempotency key
- first valid request creates one session row in PROVISIONING
- repeated identical request with same idempotency key returns the existing session rather than creating a duplicate
- invalid or missing idempotency behavior returns typed client error according to contract
- session row snapshots lab version and resume policy at creation time
- duplicate concurrent create attempts do not create multiple sessions
- integration test covers replayed request behavior

**Blockers / Dependencies**

- P0-E1-T1
- P0-E1-T2

---

## Ticket: P0-E1-T4 — Implement session metadata endpoint

**Epic:** Session Lifecycle and Control Plane Foundation
**Priority:** P0
**Estimate:** S
**Milestone Target:** Milestone 1
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec

**Description**
Implement the session metadata route so clients can fetch lifecycle state, runtime sub-state if available, interactivity, and timestamps.

**Acceptance Criteria**

- endpoint returns session metadata matching contract shape
- owner can retrieve own session metadata
- non-owner access is denied unless admin authorization is later added
- interactive flag is derived consistently from lifecycle semantics
- terminal sessions are represented correctly
- endpoint has unit/integration coverage for happy path and access denial

**Blockers / Dependencies**

- P0-E1-T1
- P0-E1-T2

---

## Ticket: P0-E1-T5 — Implement session reconciliation job

**Epic:** Session Lifecycle and Control Plane Foundation
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 2
**Owner:** TBD
**Specs:** Session Lifecycle and State Machine Spec; TDD

**Description**
Add background reconciliation that compares durable session state with runtime state and corrects drift.

**Acceptance Criteria**

- reconciliation checks active/provisioning sessions against orchestrator/runtime facts
- missing runtime for non-recoverable active session transitions to FAILED
- orphan runtime for terminal session is flagged for cleanup
- reconciliation emits structured logs or events for state corrections
- duplicate runtime condition is surfaced as critical condition
- reconciliation behavior is covered by tests for at least missing-runtime and orphan-runtime cases

**Blockers / Dependencies**

- P0-E1-T2
- runtime identity persisted in session schema
- orchestrator/runtime lookup path available

---

## Ticket: P0-E1-T6 — Implement session expiry job

**Epic:** Session Lifecycle and Control Plane Foundation
**Priority:** P0
**Estimate:** S
**Milestone Target:** Milestone 2
**Owner:** TBD
**Specs:** Session Lifecycle and State Machine Spec

**Description**
Add background expiry logic for provisioning timeout, idle timeout, and maximum session lifetime.

**Acceptance Criteria**

- provisioning timeout transitions sessions according to policy
- idle timeout transitions active sessions to IDLE or EXPIRED according to policy
- max lifetime transitions eligible sessions to EXPIRED
- expiry writes reason code and timestamp
- expired sessions reject new learner interaction
- tests cover provisioning timeout and max lifetime expiry

**Blockers / Dependencies**

- P0-E1-T2

---

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

## Ticket: P0-E3-T1 — Implement WebSocket session manager

**Epic:** Live Session Streaming
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 1
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec

**Description**
Implement the session-scoped WebSocket entry point for authorized live interaction.

**Acceptance Criteria**

- authenticated client can connect to session stream endpoint
- session ownership or equivalent temporary local rule is enforced for connection
- server sends initial SESSION\_STATUS message after connect
- connection lifecycle is logged with session correlation metadata
- unauthorized connection attempt is denied with correct behavior
- integration test covers connect, initial message, and disconnect

**Blockers / Dependencies**

- Control Plane routing baseline exists
- auth bootstrap path available or mocked for local mode

---

## Ticket: P0-E3-T2 — Implement USER\_PROMPT handling

**Epic:** Live Session Streaming
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 1
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec; Session Lifecycle and State Machine Spec

**Description**
Accept learner prompts over the session stream only when the session is interactive and no turn is already in progress.

**Acceptance Criteria**

- USER\_PROMPT is accepted only for interactive sessions
- overlapping learner turns are rejected explicitly
- prompt acceptance path creates durable learner input record or trace event
- prompt denial returns typed stream message rather than silent drop
- session not interactive returns correct denial behavior
- tests cover accepted prompt, overlapping prompt rejection, and terminal-session rejection

**Blockers / Dependencies**

- P0-E1-T2
- WebSocket session manager exists

---

## Ticket: P0-E3-T3 — Emit typed stream messages

**Epic:** Live Session Streaming
**Priority:** P0
**Estimate:** S
**Milestone Target:** Milestone 1
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec

**Description**
Support the core typed message envelope for live session delivery.

**Acceptance Criteria**

- server can emit SESSION\_STATUS
- server can emit AGENT\_TEXT\_CHUNK
- server can emit TRACE\_EVENT
- server can emit POLICY\_DENIAL and SYSTEM\_ERROR
- each message includes required envelope fields
- message serialization is covered by contract tests

**Blockers / Dependencies**

- WebSocket session manager exists

---

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

## Ticket: P0-E4-T1 — Provision staging cluster and runtime pool

**Epic:** Sandbox Runtime and Orchestration
**Priority:** P0
**Estimate:** L
**Milestone Target:** Milestone 2
**Owner:** TBD
**Specs:** Sandbox and Runtime Isolation Spec; TDD

**Description**
Provision the staging infrastructure needed to schedule isolated runtimes for sessions.

**Acceptance Criteria**

- staging cluster or equivalent runtime environment exists
- runtime pool/namespace is separated from control-plane services
- basic secrets/config path exists for non-runtime services
- environment can schedule session runtime workloads
- infrastructure is reproducible through IaC or scripted provisioning
- deployment notes are captured for future automation

**Blockers / Dependencies**

- cloud account / provider selection

---

## Ticket: P0-E4-T2 — Build lab runtime image pipeline

**Epic:** Sandbox Runtime and Orchestration
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 2
**Owner:** TBD
**Specs:** Sandbox and Runtime Isolation Spec

**Description**
Build, version, and publish approved runtime images for the supported V1 labs.

**Acceptance Criteria**

- runtime image build is automated or scriptable
- image is versioned and pinned by digest
- image scan step runs before staging promotion
- published image can be consumed by orchestrator provisioning
- disabled or revoked image is not the default launch target

**Blockers / Dependencies**

- staging registry path available

---

## Ticket: P0-E4-T3 — Implement Orchestrator provisioning path

**Epic:** Sandbox Runtime and Orchestration
**Priority:** P0
**Estimate:** L
**Milestone Target:** Milestone 2
**Owner:** TBD
**Specs:** TDD; Sandbox and Runtime Isolation Spec

**Description**
Create the orchestration path that provisions a fresh runtime from a session and lab version request.

**Acceptance Criteria**

- session launch triggers runtime provisioning request
- orchestrator launches runtime using lab-version-bound image/config
- readiness or failure is reported back to the Control Plane
- successful provisioning transitions session toward ACTIVE
- failed provisioning transitions session according to lifecycle rules
- basic integration test covers success and failure paths

**Blockers / Dependencies**

- staging runtime environment exists
- session creation path exists
- runtime image available

---

## Ticket: P0-E4-T4 — Apply baseline runtime security profile

**Epic:** Sandbox Runtime and Orchestration
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 2
**Owner:** TBD
**Specs:** Sandbox and Runtime Isolation Spec

**Description**
Enforce the baseline runtime profile for V1 lab sessions.

**Acceptance Criteria**

- runtime executes as non-root
- privilege escalation is disabled
- dropped capabilities baseline is applied
- CPU and memory limits are set
- ephemeral storage and/or PID limits are configured where supported
- forbidden mounts are not present
- verification test confirms baseline profile is active in staging

**Blockers / Dependencies**

- orchestrator provisioning path exists

---

## Ticket: P0-E4-T5 — Apply default-deny egress policy

**Epic:** Sandbox Runtime and Orchestration
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 2
**Owner:** TBD
**Specs:** Sandbox and Runtime Isolation Spec

**Description**
Restrict runtime network access to approved destinations only.

**Acceptance Criteria**

- runtime cannot reach disallowed external destinations
- runtime cannot reach PostgreSQL directly
- runtime cannot reach secret store directly
- runtime cannot reach admin-only internal APIs
- allowed destination path works for required runtime behavior
- isolation tests cover at least one allowed and multiple denied destinations

**Blockers / Dependencies**

- runtime pool/network policy mechanism available

---

## Ticket: P0-E4-T6 — Implement runtime cleanup and teardown

**Epic:** Sandbox Runtime and Orchestration
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 2
**Owner:** TBD
**Specs:** Sandbox and Runtime Isolation Spec; Session Lifecycle and State Machine Spec

**Description**
Ensure runtimes are terminated and transient resources cleaned up when sessions end or fail.

**Acceptance Criteria**

- COMPLETED, FAILED, EXPIRED, and CANCELLED sessions trigger cleanup
- cleanup removes runtime or schedules retry when immediate deletion fails
- cleanup emits structured success/failure logs
- orphan runtime condition is surfaced for operator action if retry fails repeatedly
- test covers cleanup after normal completion and abnormal failure

**Blockers / Dependencies**

- orchestrator provisioning path exists
- terminal lifecycle transitions implemented

---

# Epic 5: Agent Harness and Tool Execution

## Ticket: P0-E5-T1 — Build Agent Harness session loop

**Epic:** Agent Harness and Tool Execution
**Priority:** P0
**Estimate:** M
**Milestone Target:** Milestone 1
**Owner:** TBD
**Specs:** TDD

**Description**
Implement the core Agent Harness loop that receives learner input, constructs model requests, and streams output or tool actions.

**Acceptance Criteria**

- harness accepts one learner turn input from session runtime context
- harness builds model request using session/lab context
- harness returns streamed output or failure classification
- harness can operate for the initial supported V1 lab path
- local test covers one successful turn from prompt to model response

**Blockers / Dependencies**

- local runtime environment exists

---

## Ticket: P0-E5-T2 — Integrate model gateway provider

**Epic:** Agent Harness and Tool Execution
**Priority:** P0
**Estimate:** S
**Milestone Target:** Milestone 1
**Owner:** TBD
**Specs:** API and WebSocket Contract Spec; TDD

**Description**
Add a provider integration for model request/response streaming through the chosen gateway.

**Acceptance Criteria**

- model request can be sent to configured provider/gateway
- successful response can be streamed back in chunks
- provider failure produces typed failure classification
- configuration is environment-driven rather than hardcoded
- provider integration test covers success and failure paths

**Blockers / Dependencies**

- gateway credentials/config path available
- Agent Harness session loop baseline exists

---

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

# Intermediate Milestone (4-Day Visual Learner UI Flow)

Goal for this milestone: deliver a private-demo-ready visual learner flow where a user can open a session page, send prompts, and see streamed responses and typed status/errors.

Scope note: this milestone intentionally prioritizes demo usability over public-launch hardening (auth provider integration, network hardening, and reconciliation/expiry jobs are deferred).

## Day 1: Frontend bootstrap and session shell

- Scaffold frontend app in `apps/frontend` (recommended: Vite + React + TypeScript)
- Add route for session page (for example `/sessions/:sessionId`)
- Build page scaffold with:
  - status panel
  - transcript panel
  - prompt composer
- Add API client call to `GET /api/v1/sessions/{session_id}`
- Render initial session metadata on page load

**Day 1 done when**

- session page loads and displays metadata from backend
- baseline layout exists for status, transcript, and prompt input

## Day 2: WebSocket connect and prompt send path

- Connect to `WS /api/v1/sessions/{session_id}/stream`
- Handle initial `SESSION_STATUS` message and update status panel
- Wire prompt submit to send typed `USER_PROMPT` message over WebSocket
- Add local turn-in-flight state and disable composer while waiting

**Day 2 done when**

- client connects and receives initial status
- user can submit a prompt through WebSocket

## Day 3: Stream rendering and typed denial/error handling

- Render `AGENT_TEXT_CHUNK` incrementally in transcript
- Handle `POLICY_DENIAL` with clear user-visible message
- Handle `SYSTEM_ERROR` with visible fallback and turn reset
- Add minimal disconnect/reconnect UX state

**Day 3 done when**

- streamed chunks appear in real time
- denials and errors are surfaced clearly (no silent failure)

## Day 4: Demo polish and reliability pass

- Add loading/empty states and minor visual polish
- Add simple timestamp/status presentation improvements
- Write a short demo script (happy path + one denial/error path)
- Rehearse end-to-end flow at least twice and fix reliability issues

**Day 4 done when**

- flow is stable enough for live walkthrough
- demo script can be executed start-to-finish without manual recovery

## Milestone acceptance criteria

- learner can open a session page and see current session status
- learner can send a prompt and receive streamed response chunks live
- UI handles and displays typed denial/system-error messages
- session status/sub-state changes are visible in the UI
- end-to-end demo flow is repeatable for intermediate milestone presentation
