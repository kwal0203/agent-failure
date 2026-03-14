# Discussion: Professional Approach to Session Lifecycle State Machine

A professional engineer would treat this as a contract-first control-plane component, not just "if/else logic."

## Approach

1. Define an executable transition table from your spec.
2. Build one transition API in the Control Plane (single write path).
3. Enforce concurrency and idempotency at the storage boundary.
4. Attach side effects via outbox/events, not inline best-effort calls.
5. Add a reconciliation loop for drift between durable state and runtime.
6. Ship with a transition-matrix test suite and production-grade telemetry.

## What That Means Concretely for This Spec

### 1. Transition table as code

Create a map of `from_state + trigger -> to_state` with explicit rejects for disallowed transitions (`CREATED -> ACTIVE`, any transition out of terminal states, etc.).

This becomes the canonical source used by handlers, jobs, and reconcilers.

### 2. Single transition function

Implement one function like `transition_session(session_id, trigger, actor, metadata, idempotency_key)` that:

- reads current durable state
- validates allowed transition
- validates invariants/guards
- writes new state + reason atomically
- records transition event (audit/trace)

No other code path should update durable lifecycle state directly.

### 3. Concurrency and idempotency

Use row locking or optimistic version checks so two workers cannot both transition the same session incorrectly.

Enforce idempotency keys for launch/resume/cancel APIs and for orchestrator callbacks.

### 4. Side effects pattern

Do state commit first, then dispatch side effects through an outbox worker:

- provisioning requests
- cleanup
- alerts
- trace emission

This avoids "runtime changed but DB didn’t" inconsistencies.

### 5. Reconciler implementation

Run a periodic reconciler that compares:

- session durable state
- orchestrator runtime status
- websocket/disconnect signals
- TTL clocks

Apply only legal transitions from the same transition function.

### 6. Testing strategy

Write tests as a matrix, not ad hoc:

- allowed transitions all pass
- disallowed transitions all fail
- terminal states are terminal
- concurrent transition race tests
- idempotent replay tests
- timeout and reconciliation scenario tests

This is where most lifecycle bugs get caught.

### 7. Observability from day 1

For every transition, emit the fields already listed in your spec (`prev`, `next`, `trigger`, `actor`, `reason`, `timestamp`, `session_id`).

Add metrics:

- transition counts
- invalid transition attempts
- reconciliation corrections
- stuck-in-state durations

## Suggested next step

Turn the spec into an implementation checklist (files, interfaces, DB columns, and first test cases) and execute it incrementally.
