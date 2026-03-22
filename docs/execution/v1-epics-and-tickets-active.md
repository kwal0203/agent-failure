# V1 Epics and Tickets

## How to use this document

This document converts the V1 execution plan into implementation-ready epics and starter tickets. The epics are grouped by workstream and milestone, and the tickets are intentionally small enough to map into a backlog system without becoming vague.

Each ticket should later receive:

- owner
- priority
- estimate
- sprint or milestone target
- acceptance criteria
- links to the relevant spec

---

# Epic 1: Session Lifecycle and Control Plane Foundation

**Goal:** Establish the trusted backend core for session creation, state transitions, inspection, and reconciliation.

## Tickets

### E1-T5: Implement session history endpoint

- Add API route to fetch learner-visible session history and feedback.
- Link to: API and WebSocket Contract Spec

### E1-T6: Implement trace retrieval endpoint

- Add paginated API route for session trace retrieval.
- Link to: API and WebSocket Contract Spec

### E1-T9: Add terminal-state enforcement checks

- Prevent prompts and illegal state changes on COMPLETED, FAILED, EXPIRED, and CANCELLED sessions.
- Link to: Session Lifecycle and State Machine Spec

---

# Epic 3: Live Session Streaming

**Goal:** Support low-latency bidirectional session interaction over WebSockets.

## Tickets

### E3-T2: Implement initial session-status message

- Send session state and interactivity metadata on successful connect.
- Link to: API and WebSocket Contract Spec

### E3-T4: Implement CLIENT\_ACK handling

- Support last-event acknowledgement for replay/reconnect optimization.
- Link to: API and WebSocket Contract Spec

### E3-T5: Implement reconnect replay logic

- Replay missed learner-visible events after reconnect.
- Link to: API and WebSocket Contract Spec

### E3-T6: Enforce one interactive turn at a time

- Reject overlapping learner turns within a session.
- Link to: Session Lifecycle and State Machine Spec

---

# Epic 4: Sandbox Runtime and Orchestration

**Goal:** Provision a fresh isolated runtime per session and clean it up safely.

## Tickets

### E4-T6: Implement runtime readiness reporting

- Report provisioning success/failure and readiness to the Control Plane.
- Link to: TDD

### E4-T8: Detect orphan or duplicate runtimes

- Surface and handle isolation-risk conditions tied to one session.
- Link to: Sandbox and Runtime Isolation Spec

---

# Epic 5: Agent Harness and Tool Execution

**Goal:** Execute learner turns inside the runtime, call the model gateway, and mediate allowed tool actions.

## Tickets

### E5-T3: Implement allowed tool registry

- Define approved tools for V1 labs and reject unsupported tools.
- Link to: TDD \+ Trace Event Schema Spec

### E5-T4: Implement tool policy-denial path

- Emit TOOL\_CALL\_DENIED / POLICY\_DENIAL when tool requests violate the lab contract.
- Link to: Trace Event Schema and Evaluator Contract Spec

### E5-T5: Emit runtime and tool trace events

- Record structured tool, runtime, and model events back to the Control Plane.
- Link to: Trace Event Schema and Evaluator Contract Spec

### E5-T6: Classify provider and runtime failures

- Emit typed provider or runtime failure events for downstream handling.
- Link to: Trace Event Schema and Evaluator Contract Spec

---

# Epic 8: Authentication and Authorization

**Goal:** Secure all learner and admin workflows with identity, ownership enforcement, and privileged boundaries.

## Tickets

### E8-T1: Integrate identity provider

- Validate bearer tokens and link identities to platform users.
- Link to: Authorization and Permission Model Spec

### E8-T2: Implement role resolution

- Resolve learner/admin role and account status server-side.
- Link to: Authorization and Permission Model Spec

### E8-T3: Enforce object-level session authorization

- Restrict session metadata and history access to owner or admin.
- Link to: Authorization and Permission Model Spec

### E8-T4: Enforce object-level trace authorization

- Restrict trace access to owner or admin.
- Link to: Authorization and Permission Model Spec

### E8-T5: Enforce WebSocket authorization

- Restrict session stream connection to owner or admin.
- Link to: Authorization and Permission Model Spec

### E8-T6: Protect admin-only routes

- Restrict lab disable, session cancel, and user suspend routes to admin role.
- Link to: Authorization and Permission Model Spec

### E8-T7: Audit privileged actions

- Write durable audit records for admin state-changing operations.
- Link to: Authorization and Permission Model Spec

### E8-T8: Add ownership and negative-access tests

- Ensure guessed identifiers and route-only checks do not bypass object-level authorization.
- Link to: Authorization and Permission Model Spec

---

# Epic 9: Quota and Abuse Controls

**Goal:** Bound costly and destabilizing public usage before it harms the platform.

## Tickets

### E9-T1: Implement launch quota counters

- Track per-user launch counts and active-session caps.
- Link to: Quota and Abuse Control Spec

### E9-T2: Enforce launch admission checks

- Deny session creation before provisioning when quota or degraded-mode rules fail.
- Link to: Quota and Abuse Control Spec

### E9-T3: Implement prompt-rate limits

- Bound prompt frequency within a session and for a user where applicable.
- Link to: Quota and Abuse Control Spec

### E9-T4: Implement session-level budget guard

- Stop or deny further interactive turns once a session budget ceiling is reached.
- Link to: Quota and Abuse Control Spec

### E9-T5: Surface typed quota denials

- Return explicit QUOTA\_EXCEEDED / RATE\_LIMITED / DEGRADED\_MODE\_RESTRICTION behavior over REST and WebSocket paths.
- Link to: API and WebSocket Contract Spec

### E9-T6: Implement degraded-mode controls

- Allow admins to reduce launches or block expensive behavior under stress.
- Link to: Quota and Abuse Control Spec

### E9-T7: Emit abuse and denial metrics

- Track quota denials, suspicious launch spam, prompt flooding, and denial probing.
- Link to: Quota and Abuse Control Spec

### E9-T8: Add quota failure-mode tests

- Verify expensive work is denied before runtime creation or model execution.
- Link to: Quota and Abuse Control Spec

---

# Epic 10: Admin Operations and Governance

**Goal:** Give operators the minimum safe controls needed for support, moderation, and launch containment.

## Tickets

### E10-T1: Implement admin session inspection path

- Allow admin retrieval of session metadata, history, and trace.
- Link to: Authorization and Permission Model Spec

### E10-T2: Implement admin session cancellation

- Allow admin to cancel a learner session with audit logging.
- Link to: Authorization and Permission Model Spec

### E10-T3: Implement lab disable action

- Allow admin to disable new launches for a lab or lab version.
- Link to: Authorization and Permission Model Spec

### E10-T4: Implement user suspension action

- Allow admin to suspend a user and block future interaction.
- Link to: Authorization and Permission Model Spec

### E10-T5: Build basic admin operational panel

- Provide a minimal internal surface for key admin actions and signals.
- Link to: TDD \+ Authorization Spec

---

# Epic 11: Observability, Backup, and Release Readiness

**Goal:** Make the system deployable, diagnosable, recoverable, and launchable.

## Tickets

### E11-T1: Add structured logging across services

- Include session\_id, lab\_id, trace\_root\_id, and component metadata where appropriate.
- Link to: TDD

### E11-T2: Add core platform metrics

- Emit metrics for launches, runtime failures, evaluator backlog, quota denials, and provider errors.
- Link to: TDD \+ Quota and Abuse Control Spec

### E11-T3: Add critical alerting

- Alert on provisioning failures, DB issues, provider outages, evaluator backlog, and runtime crash spikes.
- Link to: TDD

### E11-T4: Implement backup policy for critical stores

- Enable and document backups for system-of-record data.
- Link to: TDD

### E11-T5: Run restore validation drill

- Verify recovered data is usable by the application.
- Link to: TDD

### E11-T6: Validate rollback path

- Test application and migration rollback behavior in staging.
- Link to: Execution Plan

### E11-T7: Run staging soak test

- Exercise the platform over time with multi-session traffic and failure checks.
- Link to: Execution Plan

### E11-T8: Prepare launch checklist inputs

- Gather evidence for launch gates, including test passes, restore validation, and containment controls.
- Link to: Execution Plan

---

# Epic 12: CI/CD and Developer Workflow

**Goal:** Ensure the team can build, test, and ship the platform consistently.

## Tickets

### E12-T1: Set up backend CI pipeline

- Run tests, linting, and type checks on backend changes.
- Link to: TDD

### E12-T2: Set up frontend CI pipeline

- Run frontend tests and build checks on UI changes.
- Link to: TDD

### E12-T3: Set up image build and scan pipeline

- Build and scan Control Plane and runtime images before staging promotion.
- Link to: Sandbox and Runtime Isolation Spec

### E12-T4: Set up staged deployment workflow

- Promote services and configs into staging through a controlled path.
- Link to: TDD

### E12-T5: Add migration execution safety checks

- Ensure DB migrations run in safe order and can be rolled back where possible.
- Link to: TDD

---

# Suggested initial priority order

## P0 foundation

- Epic 1: Session Lifecycle and Control Plane Foundation
- Epic 3: Live Session Streaming
- Epic 4: Sandbox Runtime and Orchestration
- Epic 5: Agent Harness and Tool Execution

## P1 product viability

- Epic 2: Learner UI Vertical Slice
- Epic 6: Trace Pipeline and Replay
- Epic 7: Evaluator and Feedback Pipeline

## P1 public-safety boundary

- Epic 8: Authentication and Authorization
- Epic 9: Quota and Abuse Controls
- Epic 10: Admin Operations and Governance

## P1 launch readiness

- Epic 11: Observability, Backup, and Release Readiness
- Epic 12: CI/CD and Developer Workflow
