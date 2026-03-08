# Session Lifecycle and State Machine Specification

## Purpose

This document defines the lifecycle of a lab session in the AI agent security lab platform. Its purpose is to give all platform components a shared contract for how a session is created, becomes interactive, processes learner turns, handles failure, supports resume where allowed, and terminates safely.

This spec is intentionally lower-level than the PRD and TDD. It is written to remove ambiguity for implementation, testing, observability, and operations.

## Scope

This specification covers:

- durable session states  
- transient runtime sub-states for active sessions  
- allowed state transitions  
- transition triggers  
- ownership of state changes  
- invariants that must always hold  
- side effects attached to transitions  
- reconciliation behavior when durable state and runtime state diverge  
- timeout, expiry, failure, and resume semantics

This specification does not define:

- detailed API payload schemas  
- exact database DDL  
- detailed Kubernetes manifests  
- evaluator rule content

## Core principles

- A session has exactly one durable lifecycle state at a time.  
- The Control Plane is the source of truth for durable session state.  
- The frontend never authoritatively changes session state.  
- The Orchestrator and Agent Harness may report runtime facts, but only the Control Plane persists lifecycle transitions.  
- Runtime and evaluator events must be interpreted relative to the current durable session state.  
- A transition may trigger side effects, but side effects do not become authoritative until the Control Plane commits the resulting state.  
- Resume behavior must be explicit and lab-version dependent.

## Session identity

A session represents one learner’s run of one published lab version.

A session is uniquely associated with:

- one learner  
- one lab  
- one lab version  
- one resume policy snapshot  
- one durable trace stream  
- zero or one active lab containers at a given point in time

A session is not reused across learners and is not repurposed for a different lab version.

## Durable lifecycle states

The following durable states are authoritative and stored in the session record.

### `CREATED`

The session record exists but provisioning has not yet started.

### `PROVISIONING`

The Control Plane has accepted the launch request and the Orchestrator is creating the lab runtime.

### `ACTIVE`

The session is interactive. The learner may connect, submit prompts subject to turn rules, and receive streamed output and feedback.

### `IDLE`

The session remains resumable, but there is currently no active learner turn and the runtime may be waiting for input, disconnected, or nearing expiry according to policy.

### `COMPLETED`

The session reached a natural terminal condition according to lab success/failure completion semantics and no further learner interaction is allowed.

### `FAILED`

The session terminated abnormally due to provisioning failure, runtime failure, unrecoverable persistence error, or another terminal system fault.

### `EXPIRED`

The session exceeded time-based or policy-based lifetime limits and is no longer interactive.

### `CANCELLED`

The session was intentionally terminated by an authorized administrative action or explicit learner cancellation if that capability is later supported.

## Transient runtime sub-states

These sub-states are not the primary durable lifecycle state, but they are useful for control logic and observability while the session is `ACTIVE` or `IDLE`.

### `WAITING_FOR_INPUT`

The session is interactive and ready to accept a learner prompt.

### `RUNNING_AGENT_TURN`

A learner turn is in progress. The Agent Harness may be streaming model output, executing tool calls, or both.

### `STREAMING_OUTPUT`

Model output is actively streaming to the learner.

### `EXECUTING_TOOL`

The Agent Harness is executing one or more tool calls allowed by the lab contract.

### `DELIVERING_FEEDBACK`

Learner-visible feedback is being pushed from the evaluation pipeline or another feedback source.

### `DISCONNECTED_RESUMABLE`

The learner client is disconnected, but the session remains eligible for reconnect or resume according to policy.

These sub-states may be represented as runtime flags, an auxiliary session\_runtime table, or derived process state. They must not contradict the durable lifecycle state.

## Canonical state-transition graph

Allowed durable transitions are:

- `CREATED -> PROVISIONING`  
    
- `CREATED -> FAILED`  
    
- `CREATED -> CANCELLED`  
    
- `PROVISIONING -> ACTIVE`  
    
- `PROVISIONING -> FAILED`  
    
- `PROVISIONING -> CANCELLED`  
    
- `PROVISIONING -> EXPIRED` only if provisioning TTL is exceeded and policy maps timeout to expiry instead of failure  
    
- `ACTIVE -> IDLE`  
    
- `ACTIVE -> COMPLETED`  
    
- `ACTIVE -> FAILED`  
    
- `ACTIVE -> EXPIRED`  
    
- `ACTIVE -> CANCELLED`  
    
- `IDLE -> ACTIVE`  
    
- `IDLE -> COMPLETED`  
    
- `IDLE -> FAILED`  
    
- `IDLE -> EXPIRED`  
    
- `IDLE -> CANCELLED`  
    
- `FAILED` is terminal  
    
- `COMPLETED` is terminal  
    
- `EXPIRED` is terminal  
    
- `CANCELLED` is terminal

No other durable transitions are allowed without an explicit revision to this specification.

## Transition definitions

### 1\. Session creation

**Transition**: `CREATED -> PROVISIONING`

**Trigger**:

- learner requests a new session  
- request passes authentication, authorization, quota, and lab-availability checks

**Owner**:

- Control Plane

**Required checks**:

- learner is authenticated  
- learner is authorized to launch the lab  
- lab is published and launchable  
- session creation is within quota and platform policy  
- idempotency key is valid

**Side effects**:

- create durable session row if not already present  
- snapshot lab version and resume policy  
- initialize trace root  
- emit audit or operational launch event  
- send provisioning request to Orchestrator

### 2\. Provisioning success

**Transition**: `PROVISIONING -> ACTIVE`

**Trigger**:

- Orchestrator reports runtime ready  
- runtime health checks pass  
- Agent Harness bootstrap succeeds

**Owner**:

- Control Plane, based on Orchestrator signal

**Side effects**:

- persist runtime identity metadata  
- mark session interactive  
- initialize runtime sub-state as `WAITING_FOR_INPUT`  
- emit session-ready trace event

### 3\. Provisioning failure

**Transition**: `PROVISIONING -> FAILED`

**Trigger**:

- pod/container creation failure  
- readiness timeout  
- bootstrap failure  
- unrecoverable configuration error

**Owner**:

- Control Plane, based on Orchestrator or bootstrap signal

**Side effects**:

- persist failure reason category and details  
- emit failure event  
- schedule cleanup of transient resources

### 4\. Learner disconnect or inactivity

**Transition**: `ACTIVE -> IDLE`

**Trigger**:

- learner disconnects and no active turn is running, or  
- active session exceeds idle threshold while resumable, or  
- session is waiting for learner input and product policy classifies it as idle

**Owner**:

- Control Plane via session watchdog/reconciliation logic

**Side effects**:

- persist last-known resume point  
- mark runtime sub-state as `DISCONNECTED_RESUMABLE` or equivalent if applicable  
- keep runtime alive or mark for warm reconstruction according to lab policy

### 5\. Reconnect/resume to interactive state

**Transition**: `IDLE -> ACTIVE`

**Trigger**:

- learner reconnects to a resumable session  
- session has not expired or been cancelled  
- runtime still exists or reconstruction succeeds under resume policy

**Owner**:

- Control Plane

**Side effects**:

- if hot resume, reattach to existing runtime stream  
- if warm reconstruction, provision fresh runtime and restore allowed durable state  
- emit resume trace event with resume mode  
- mark runtime sub-state as `WAITING_FOR_INPUT`

### 6\. Successful completion

**Transition**: `ACTIVE -> COMPLETED` or `IDLE -> COMPLETED`

**Trigger**:

- lab success criteria met and product policy treats that as terminal, or  
- lab reaches explicit terminal condition with no further interaction allowed

**Owner**:

- Control Plane based on evaluation outcome or lab terminal event

**Side effects**:

- persist completion reason and final outcome  
- stop accepting learner prompts  
- schedule runtime cleanup  
- keep learner-visible trace and results available according to retention policy

### 7\. Runtime failure after activation

**Transition**: `ACTIVE -> FAILED` or `IDLE -> FAILED`

**Trigger**:

- runtime crash  
- unrecoverable Agent Harness error  
- critical persistence failure that invalidates safe continuation  
- reconciliation detects missing runtime where resume policy does not allow recovery

**Owner**:

- Control Plane based on runtime or infrastructure signal

**Side effects**:

- persist failure reason  
- emit failure trace event  
- stop accepting prompts  
- schedule cleanup and operator alerting if required

### 8\. Expiry

**Transition**: `ACTIVE -> EXPIRED` or `IDLE -> EXPIRED` or `PROVISIONING -> EXPIRED`

**Trigger**:

- maximum session duration exceeded  
- idle TTL exceeded  
- provisioning TTL exceeded where policy maps to expiry

**Owner**:

- Control Plane via background expiry job

**Side effects**:

- stop accepting prompts  
- record expiry reason  
- terminate or clean up runtime  
- preserve learner-visible history according to retention policy

### 9\. Administrative cancellation

**Transition**: `CREATED|PROVISIONING|ACTIVE|IDLE -> CANCELLED`

**Trigger**:

- authorized operator terminates session due to moderation, abuse, incident response, or manual support action

**Owner**:

- Control Plane after authorization check

**Side effects**:

- write audit log  
- stop accepting prompts  
- instruct Orchestrator to terminate runtime if present  
- emit cancellation event

## Disallowed transitions

The following are explicitly disallowed:

- any transition out of `COMPLETED`  
- any transition out of `FAILED`  
- any transition out of `EXPIRED`  
- any transition out of `CANCELLED`  
- `PROVISIONING -> IDLE`  
- `CREATED -> ACTIVE`  
- `ACTIVE -> PROVISIONING`  
- `IDLE -> PROVISIONING`  
- `COMPLETED -> ACTIVE`  
- `FAILED -> ACTIVE`

If future product behavior needs “restart,” it must create a new session or explicitly introduce a new state and migration plan.

## Turn-processing rules within ACTIVE

While a session is in `ACTIVE`, learner interaction must still follow stricter runtime rules.

### Turn invariant

Only one learner turn may be in progress at a time for a given session.

### Allowed runtime sequence

A typical sequence is:

- `WAITING_FOR_INPUT`  
- learner prompt accepted  
- `RUNNING_AGENT_TURN`  
- optional `STREAMING_OUTPUT`  
- optional `EXECUTING_TOOL`  
- optional repeated output/tool cycles  
- turn finalization  
- `WAITING_FOR_INPUT`

### Prompt acceptance rules

A new learner prompt may be accepted only if:

- session durable state is `ACTIVE`  
- runtime sub-state is compatible with a new turn, typically `WAITING_FOR_INPUT`  
- no turn lock is held  
- quota and policy checks pass

### Denial rules

A learner prompt must be rejected if:

- session is not `ACTIVE`  
- another turn is still in progress  
- session is expired, failed, completed, or cancelled  
- per-session or per-user quota is exceeded  
- lab policy disallows the requested action

## Ownership of state changes

### Control Plane

The Control Plane is the only component allowed to persist durable lifecycle transitions.

### Orchestrator

The Orchestrator reports runtime facts such as provisioning success, readiness failure, crash, or termination. It does not directly mutate durable session state.

### Agent Harness

The Agent Harness reports runtime events, tool actions, and fatal runtime faults. It does not directly mutate durable lifecycle state.

### Evaluation pipeline

The evaluator may produce outcomes that cause the Control Plane to transition a session to `COMPLETED`, but the evaluator does not directly write terminal lifecycle state unless the Control Plane owns and validates that write path.

### Frontend

The frontend may request actions such as launch, reconnect, or prompt submission, but it never authoritatively changes session state.

## Invariants

The following invariants must always hold.

### Identity invariants

- A session belongs to exactly one learner.  
- A session points to exactly one lab version.  
- A session has exactly one durable lifecycle state at a time.

### Runtime invariants

- At most one active runtime is attached to a session at a time unless a future migration explicitly supports handoff semantics.  
- At most one learner turn is in progress at a time per session.  
- A runtime that belongs to a non-interactive terminal session must not accept new prompts.

### Persistence invariants

- Durable trace ordering is monotonic within a session.  
- Lifecycle transitions are persisted before user-visible state is treated as authoritative.  
- Session completion or failure reason must be durably stored before cleanup deletes the runtime.

### Authorization invariants

- Only the owner or an authorized admin may access session history.  
- Only an authorized admin may cancel another learner’s session.

### Resume invariants

- Resume mode must be explicit: hot resume, warm reconstruction, or not supported.  
- Reconstructed sessions must not expose ephemeral state that was not declared durable by policy.  
- A learner must never be attached to another learner’s runtime or trace stream.

## Resume semantics

Resume policy is snapshotted from the lab version at session creation time.

### Hot resume

The existing runtime still exists. The learner reconnects to the same session runtime and continues.

### Warm reconstruction

The original runtime no longer exists, but the lab permits reconstruction from durable state. A fresh runtime is provisioned and only declared durable state is restored.

### No resume

The lab or session policy does not permit continuation after disconnect, expiry, or runtime loss.

### Durable vs ephemeral state classes

**Durable by default**:

- session metadata  
- learner prompts and model outputs already committed to trace  
- evaluation outcomes already committed  
- lab version reference  
- declared accepted artifact references if artifacts are part of V1 in the future

**Ephemeral by default**:

- process memory inside runtime  
- uncommitted streaming chunks  
- temporary filesystem mutations unless explicitly snapshotted  
- live network connections  
- partial tool execution state not yet committed as durable output

## Timeout and expiry semantics

### Provisioning timeout

A session may remain in `PROVISIONING` only until the provisioning TTL elapses. After that it transitions to `FAILED` or `EXPIRED` according to configured policy.

### Idle timeout

A session in `ACTIVE` or `IDLE` that receives no qualifying learner activity for the idle TTL transitions to `IDLE` or `EXPIRED` depending on the current state and policy.

### Maximum session lifetime

A session may not remain interactive beyond its maximum allowed age. Once exceeded, it transitions to `EXPIRED` even if the learner is still connected.

### Turn timeout

An individual learner turn may have a maximum duration. If exceeded, the Control Plane records a turn-timeout event, attempts safe interruption if supported, and either returns to `WAITING_FOR_INPUT`, moves to `IDLE`, or transitions to `FAILED` depending on failure severity.

## Reconciliation behavior

Because runtime truth and durable state can diverge, a reconciliation loop is required.

### Reconciliation inputs

- session table  
- Orchestrator runtime status  
- heartbeat or liveness signals  
- WebSocket connection state  
- evaluator outcomes  
- cleanup task outcomes

### Reconciliation rules

- If durable state is `ACTIVE` but runtime is gone and reconstruction is not allowed, transition to `FAILED`.  
- If durable state is `ACTIVE` but learner is disconnected and idle threshold is exceeded, transition to `IDLE`.  
- If durable state is `IDLE` and runtime is missing but warm reconstruction is supported, remain `IDLE` until learner reconnects or expiry occurs.  
- If durable state is terminal and runtime still exists, cleanup should be retried until the runtime is removed.  
- If duplicate runtimes are detected for one session, mark the condition critical, prevent new interaction, and require operator or automated containment according to incident policy.

## Observability requirements

For every lifecycle transition, the platform must record:

- session id  
- previous durable state  
- next durable state  
- trigger category  
- actor or subsystem responsible  
- reason code  
- timestamp  
- correlation id or trace root id where applicable

Metrics should include:

- provisioning success/failure counts  
- active sessions  
- idle sessions  
- completion counts by lab  
- failure counts by failure category  
- resume attempts and resume success by mode  
- expiry counts  
- reconciliation corrections

## Error classification

Session-terminal failures should be classified into categories such as:

- provisioning\_failure  
- bootstrap\_failure  
- runtime\_crash  
- policy\_block\_terminal  
- persistence\_failure  
- provider\_failure\_terminal  
- reconciliation\_failure  
- administrative\_cancellation

The exact set may evolve, but failures must be categorized, not only stored as opaque text.

## Testing requirements

The following tests are required for this lifecycle spec.

### State-transition tests

- every allowed transition succeeds when preconditions hold  
- every disallowed transition is rejected  
- terminal states reject new prompts and lifecycle regression

### Concurrency tests

- duplicate launch requests with same idempotency key do not create duplicate sessions  
- concurrent prompts in one session do not run overlapping turns  
- reconnect during active turn preserves session correctness

### Timeout tests

- provisioning timeout transitions correctly  
- idle timeout transitions correctly  
- max-lifetime expiry transitions correctly

### Resume tests

- hot resume reconnects correctly  
- warm reconstruction restores only allowed durable state  
- no-resume labs correctly deny continuation

### Reconciliation tests

- missing runtime is detected and corrected  
- orphan runtime after terminal state is cleaned up  
- duplicate runtime condition is surfaced and contained

## Open design choices for implementation

The following implementation choices remain open but must preserve this lifecycle contract:

- whether transient sub-states are persisted or derived  
- whether turn locks are DB-backed, in-memory with fencing, or queue-based  
- whether reconciliation runs on polling, event-driven hooks, or both  
- whether evaluator-triggered completion is written through a dedicated session-state service or directly through a validated Control Plane path

## Summary

This state machine exists to ensure that learner interaction, runtime orchestration, trace persistence, evaluation, and operations all reason about the same session semantics. Any implementation that diverges from these durable states, allowed transitions, invariants, or ownership rules is non-compliant with the platform design.  
