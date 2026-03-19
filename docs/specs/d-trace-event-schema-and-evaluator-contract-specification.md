# Trace Event Schema and Evaluator Contract Specification

## Purpose

This document defines the structured trace model and evaluator contract for the AI agent security lab platform. Its purpose is to make event capture, replay, analysis, and constraint-based feedback consistent across the Control Plane, Agent Harness, Orchestrator, and evaluation pipeline.

This specification is lower-level than the PRD and TDD. It describes what events must be recorded, how they are ordered and versioned, what fields are required, how evaluators consume them, and how evaluator outputs become learner-visible feedback and durable outcomes.

## Scope

This specification covers:

- trace-event goals and design principles
- canonical event envelope
- event ordering and durability rules
- required event families and message semantics
- session-level event invariants
- evaluator inputs and outputs
- evaluator triggering and idempotency
- feedback delivery semantics
- versioning and backward-compatibility requirements
- testing requirements

This specification does not define:

- exact database DDL
- the full content of every lab-specific constraint bundle
- UI rendering details for traces or feedback
- internal LLM prompting strategy beyond what must be represented in events

## Core principles

- Trace events are a durable, structured account of what happened in a session.
- A trace is not only a debug log; it is also an instructional artifact and an evaluation input.
- Events must be meaningful enough for replay, debugging, and evaluation without requiring raw container access.
- The Control Plane is authoritative for durable event ordering.
- Evaluators consume committed trace events only.
- Lab-specific evaluation must be version-stable: a session is interpreted against the lab version that produced it.
- Learner-visible feedback should be grounded in observable events and state changes, not only free-form judgments.
- Event schemas should be extensible, but existing semantics must remain backward-compatible once clients depend on them.

## Trace model overview

A session trace is an ordered stream of durable events associated with one session and one lab version.

Each session has:

- one `session_id`
- one `trace_root_id`
- one monotonically increasing `event_index` sequence
- one lab version that determines evaluation semantics

A trace may include events emitted by:

- the Control Plane
- the Agent Harness
- the Orchestrator
- the evaluator

The trace is the canonical source for:

- replaying learner-visible session history
- reconstructing major runtime decisions
- evaluating constraint violations and success criteria
- debugging session failures and operational issues

## Event ordering and durability

### Ordering rules

- Every durable event in a session trace must have a session-scoped `event_index`.
- `event_index` values are strictly increasing within a session.
- No ordering guarantee is required across sessions.
- Evaluator outputs that refer to prior events must include the triggering `event_index` or event range.

### Durability rules

- Events relevant to replay, evaluation, or operational debugging must be durably persisted.
- The Control Plane is responsible for assigning durable order, even when event content originates elsewhere.
- The evaluator must consume only committed events.
- Live streaming may expose events with low latency, but durable persistence is the source of truth.

### Replay rules

- Replay endpoints and reconnect paths must use durable event order.
- If live delivery diverges from what was durably committed, the durable trace wins.

## Canonical event envelope

All durable trace events must conform to a common envelope.

### Required fields

- `event_id`: unique identifier for the event
- `session_id`: owning session id
- `trace_root_id`: stable trace grouping identifier for the session
- `event_index`: monotonically increasing index within the session
- `event_type`: stable machine-readable event type
- `event_version`: schema version for the event payload
- `source`: emitting subsystem
- `timestamp`: server-side committed timestamp
- `payload`: typed event payload

### Recommended optional fields

- `correlation_id`: ties related events within a learner turn or tool cycle
- `request_id`: request or stream-level identifier where useful
- `actor_type`: e.g. learner, model, system, admin
- `lab_version_id`: may be included redundantly for convenience
- `visibility`: learner\_visible, admin\_only, or internal
- `sensitivity`: optional classification for later handling

### Allowed sources

- `control_plane`
- `agent_harness`
- `orchestrator`
- `evaluator`

### Example envelope

{

  "event\_id": "uuid",

  "session\_id": "uuid",

  "trace\_root\_id": "uuid",

  "event\_index": 42,

  "event\_type": "TOOL\_CALL\_EXECUTED",

  "event\_version": 1,

  "source": "agent\_harness",

  "timestamp": "2026-03-07T18:10:00Z",

  "payload": {

    "tool\_name": "read\_file",

    "arguments": {

      "path": "/workspace/notes.txt"

    }

  }

}

## Event families

The platform must support the following event families in V1.

### 1\. Session lifecycle events

These events capture major session-state transitions and lifecycle milestones.

Examples:

- `SESSION_CREATED`
- `SESSION_PROVISIONING_STARTED`
- `SESSION_ACTIVE`
- `SESSION_IDLE`
- `SESSION_COMPLETED`
- `SESSION_FAILED`
- `SESSION_EXPIRED`
- `SESSION_CANCELLED`
- `SESSION_RESUMED`

**Required payload fields**:

- previous state where applicable
- next state
- reason code if transition is not the happy path
- resume mode where applicable

### 2\. Learner interaction events

These capture learner-originated actions relevant to the instructional record.

Examples:

- `LEARNER_PROMPT_ACCEPTED`
- `LEARNER_PROMPT_REJECTED`
- `LEARNER_DISCONNECTED`
- `LEARNER_RECONNECTED`

**Required payload fields for prompt acceptance**:

- message id or request id
- learner-visible content or a content reference
- turn correlation id

**Required payload fields for prompt rejection**:

- rejection code
- rejection reason category
- whether retryable

### 3\. Model interaction events

These capture the model-side interaction controlled by the Agent Harness.

Examples:

- `MODEL_REQUEST_STARTED`
- `MODEL_RESPONSE_CHUNK`
- `MODEL_RESPONSE_COMPLETED`
- `MODEL_RESPONSE_ABORTED`
- `MODEL_PROVIDER_ERROR`

**Required payload fields**:

- provider/model identifier where safe and relevant
- correlation id for the learner turn
- chunk ordering metadata for chunked outputs
- finalization reason for completed or aborted outputs

### 4\. Tool and policy events

These capture model-requested tool actions and policy outcomes.

Examples:

- `TOOL_CALL_REQUESTED`
- `TOOL_CALL_DENIED`
- `TOOL_CALL_EXECUTION_STARTED`
- `TOOL_CALL_EXECUTED`
- `TOOL_CALL_FAILED`
- `POLICY_DENIAL`

**Required payload fields**:

- tool name
- normalized tool arguments or a safe reference to them
- denial code if denied
- execution result summary if executed
- failure category if failed

### 5\. Environment and runtime events

These capture observable environment state changes relevant to labs and operations.

Examples:

- `RUNTIME_READY`
- `RUNTIME_HEARTBEAT_MISSED`
- `RUNTIME_CRASH_DETECTED`
- `FILESYSTEM_STATE_CHANGED`
- `RETRIEVAL_QUERY_EXECUTED`
- `RETRIEVAL_RESULT_RETURNED`

Only environment events that are instructionally useful, operationally useful, or evaluator-relevant should be persisted. The platform should avoid unbounded noisy event emission.

### 6\. Evaluation and feedback events

These capture constraint-based interpretation of trace activity.

Examples:

- `EVALUATION_TRIGGERED`
- `CONSTRAINT_VIOLATION_DETECTED`
- `SUCCESS_SIGNAL_DETECTED`
- `FEEDBACK_PUBLISHED`
- `SESSION_TERMINAL_OUTCOME_ASSIGNED`

**Required payload fields**:

- evaluator version or constraint bundle reference
- triggering event index or event range
- constraint or success-signal identifier
- result category
- feedback level where applicable

### 7\. Administrative and governance events

These capture privileged operational actions relevant to a session.

Examples:

- `ADMIN_SESSION_INSPECTED`
- `ADMIN_SESSION_CANCELLED`
- `DEGRADED_MODE_BLOCK_APPLIED`

These events may be learner-hidden while remaining part of the auditable session or governance record where appropriate.

## Event visibility and redaction

Not every durable event must be learner-visible in raw form.

### Visibility levels

- `learner_visible`: may be shown in trace viewer or live stream
- `admin_only`: visible only to authorized operators
- `internal`: retained for system correctness or operations, not directly shown to learners

### Redaction principles

- Sensitive internal metadata should not leak into learner-visible events.
- Raw secrets, privileged tokens, or internal service addresses must never appear in trace payloads.
- If an event contains sensitive implementation details needed operationally but not pedagogically, the system should store a redacted learner-visible projection and retain the fuller internal version only where policy allows.

## Payload design rules

- Payloads must be typed and stable for their event type and version.
- Free-form text alone is insufficient for key events; typed fields should exist for evaluators and analytics.
- Event payloads should capture normalized facts rather than ad hoc prose where feasible.
- Large artifacts should be referenced by durable IDs rather than embedded directly in the event.
- Payloads must remain small enough for efficient storage and replay.

## Session-level invariants

The following invariants must hold for trace emission.

### Ordering invariants

- No duplicate `event_index` within a session.
- No event may appear durably between two already committed indices.
- Evaluator outputs must refer only to existing committed events.

### Causality invariants

- A `TOOL_CALL_EXECUTED` or `TOOL_CALL_DENIED` must correspond to a prior tool-request context within the same turn correlation where applicable.
- A `SESSION_COMPLETED`, `SESSION_FAILED`, `SESSION_EXPIRED`, or `SESSION_CANCELLED` event must not be followed by new learner prompt acceptance events.
- A `MODEL_RESPONSE_COMPLETED` should correspond to a started response unless explicitly marked synthetic or recovered.

### Visibility invariants

- Learner-visible history must be derivable from learner-visible or transformed durable events.
- Internal-only events must not leak through learner-visible APIs.

## Evaluator contract overview

Evaluators interpret committed trace events for one lab version and produce durable evaluation outputs.

An evaluator is responsible for:

- reading committed trace events for a session
- loading the matching lab-version evaluation bundle
- determining whether a constraint violation, success condition, partial success, or no-action result occurred
- writing durable evaluation outputs idempotently
- optionally publishing learner-visible feedback

Evaluators are not responsible for:

- reordering trace history
- mutating raw trace events
- bypassing the Control Plane’s session lifecycle authority

## Evaluator input contract

For each evaluation task, the evaluator must have access to:

- `session_id`
- `lab_version_id`
- committed trace events in session order
- evaluator/constraint bundle version
- any declared durable session metadata required by the lab contract

The evaluator must not depend on ephemeral runtime state that was never durably recorded unless the lab explicitly declares a separate evaluator input source.

## Evaluator output contract

Evaluator outputs must be durable, typed, and refer back to the triggering trace context.

### Required output fields

- `evaluation_result_id`
- `session_id`
- `lab_version_id`
- `evaluator_version`
- `result_type`
- `constraint_id` or `signal_id`
- `trigger_event_index` or `trigger_event_range`
- `feedback_level`
- `feedback_payload`
- `created_at`

### Result types

At minimum, V1 should support:

- `constraint_violation`
- `success_signal`
- `partial_success`
- `no_effect`
- `terminal_outcome`

### Feedback levels

A suggested V1 scale is:

- `none`
- `flag`
- `hint`
- `detailed_hint`

## Evaluator triggering semantics

### Triggering model

The first release may use one of these models:

- evaluate after every newly committed event window
- evaluate after turn-finalization events
- hybrid model where lightweight checks run continuously and heavier checks run at turn boundaries

Regardless of implementation, the contract must guarantee:

- evaluators only read committed events
- repeated evaluation attempts over the same event range are safe
- duplicate durable outputs are prevented or collapsed idempotently

### Idempotency rules

An evaluator rerun over the same triggering context must not create duplicate learner-visible feedback or conflicting terminal outcomes.

Idempotency keys should incorporate at least:

- session id
- evaluator version
- constraint or signal id
- triggering event index or event range

## Terminal-outcome semantics

Evaluators may determine that a session has reached a terminal instructional outcome, but the evaluator should not directly own session-lifecycle state.

### Allowed pattern

1. evaluator writes a durable `terminal_outcome` result
2. Control Plane or a validated session-state service consumes that result
3. Control Plane decides whether to transition the session to `COMPLETED`

This preserves lifecycle authority while still allowing evaluation-driven completion.

## Feedback-delivery semantics

### Live delivery

If the session is active and connected, learner-visible feedback may be streamed over the WebSocket after the triggering event.

### Durable delivery

All learner-visible feedback must also be durably stored so it can be retrieved through session-history endpoints.

### Ordering rules

- Feedback may arrive after the triggering event.
- Feedback should reference the relevant `event_index` or event range.
- Feedback must not appear to refer to future events.

### Suppression and deduplication

The evaluator or Control Plane may suppress repeated equivalent feedback if the same constraint is triggered repeatedly in a short window, provided the durable evaluation semantics remain correct.

## Lab-version and schema-version compatibility

### Lab-version binding

Every session is bound to one `lab_version_id`, and evaluation must use the corresponding versioned constraint bundle.

### Event-version handling

- Each event type must carry an `event_version`.
- Consumers must handle supported versions explicitly.
- Backward-incompatible changes require a new version with a migration or compatibility path.

### Evaluator-version handling

- Evaluator outputs must record the evaluator version used.
- A later evaluator version must not silently reinterpret historical sessions without explicit reprocessing policy.

## Recommended event-type catalog for V1

A minimal but sufficient V1 catalog includes:

- `SESSION_CREATED`
- `SESSION_PROVISIONING_STARTED`
- `SESSION_ACTIVE`
- `SESSION_IDLE`
- `SESSION_COMPLETED`
- `SESSION_FAILED`
- `SESSION_EXPIRED`
- `SESSION_CANCELLED`
- `SESSION_RESUMED`
- `LEARNER_PROMPT_ACCEPTED`
- `LEARNER_PROMPT_REJECTED`
- `MODEL_REQUEST_STARTED`
- `MODEL_RESPONSE_CHUNK`
- `MODEL_RESPONSE_COMPLETED`
- `MODEL_PROVIDER_ERROR`
- `TOOL_CALL_REQUESTED`
- `TOOL_CALL_DENIED`
- `TOOL_CALL_EXECUTION_STARTED`
- `TOOL_CALL_EXECUTED`
- `TOOL_CALL_FAILED`
- `POLICY_DENIAL`
- `RUNTIME_READY`
- `RUNTIME_CRASH_DETECTED`
- `CONSTRAINT_VIOLATION_DETECTED`
- `SUCCESS_SIGNAL_DETECTED`
- `FEEDBACK_PUBLISHED`
- `SESSION_TERMINAL_OUTCOME_ASSIGNED`

This catalog may expand, but V1 implementations should avoid uncontrolled proliferation of semantically overlapping event types.

## Testing requirements

### Trace-schema tests

- every emitted event conforms to its schema version
- required fields exist for each event family
- event ordering is strictly monotonic within a session
- learner-visible events are correctly filtered or transformed from durable events

### Evaluator tests

- evaluator consumes only committed events
- evaluator produces idempotent outputs for repeated triggering contexts
- evaluator outputs reference valid triggering event indices
- evaluator uses the correct lab version and evaluator version

### End-to-end tests

- learner prompt, model response, tool call, and feedback chain produces a coherent durable trace
- replay from durable history preserves causal ordering
- session completion triggered by evaluation produces both evaluation output and proper lifecycle transition through the Control Plane

### Negative tests

- internal-only events do not leak through learner trace APIs
- terminal sessions do not receive new learner prompt acceptance events
- malformed or unknown event versions are rejected or safely quarantined according to policy

## Open implementation choices

The following implementation choices may vary as long as this contract remains true:

- whether some event families are normalized into separate tables in addition to a general trace table
- whether model chunks are stored at fine granularity or coalesced after streaming completion
- whether evaluator triggering uses polling, pub/sub, or turn-finalization hooks
- whether some operational events are stored in a separate audit/governance stream as well as the session trace

## Summary

This specification ensures that the platform records meaningful, ordered, versioned session events and that evaluators interpret those events in a durable, reproducible, and instructionally grounded way. Any implementation that emits ad hoc logs without stable semantics, evaluates against uncommitted or wrong-version data, or produces feedback that cannot be tied back to observable trace context is non-compliant with the platform design.
