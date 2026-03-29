# Current Plan: Post-Milestone Reliability and Safety

## Context
The immediate implementation sequence and intermediate visual UI milestone are complete.
The next phase should harden runtime/session correctness before broader beta-facing work.

## Priority Goal
Stabilize lifecycle correctness and runtime safety in staging-equivalent flow.

## Recommended Ticket Chunk (next)
1. P0-E4-T6 Implement runtime cleanup and teardown
2. P0-E1-T5 Implement session reconciliation job
3. P0-E1-T6 Implement session expiry job
4. P0-E4-T4 Apply baseline runtime security profile
5. P0-E4-T5 Apply default-deny egress policy

## Why this chunk first
- Current path proves happy-path interaction; biggest remaining risk is failure-path drift.
- Cleanup + reconciliation + expiry make session state trustworthy under real failures.
- Runtime security profile + egress policy are the minimum safety controls for staging confidence.

## 7-Day Execution Plan

### Day 1: P0-E4-T6 Runtime cleanup/teardown
- Define cleanup triggers for terminal states (COMPLETED/FAILED/EXPIRED/CANCELLED).
- Implement cleanup dispatch path and retry bookkeeping.
- Add tests for normal completion cleanup and failed cleanup retry path.
- Exit gate: terminal sessions trigger cleanup deterministically.

### Day 2-3: P0-E1-T5 Session reconciliation job
- Implement periodic reconciliation worker:
  - DB says active/provisioning but runtime missing -> legal transition via lifecycle service.
  - DB says terminal but runtime exists -> issue cleanup again.
  - duplicate runtime detection -> structured critical signal.
- Ensure fixes go through transition service/state machine (no ad hoc DB edits).
- Add integration tests for missing-runtime and orphan-runtime cases.
- Exit gate: reconciliation can self-heal common drift scenarios.

### Day 4: P0-E1-T6 Session expiry job
- Implement provisioning timeout, idle timeout, max-lifetime scans.
- Trigger legal transitions with reason codes and timestamps via transition service.
- Add tests for provisioning timeout and max-lifetime expiry minimum.
- Exit gate: stale sessions transition consistently and reject invalid interaction.

### Day 5: P0-E4-T4 Runtime baseline security profile
- Enforce non-root runtime, no privilege escalation, dropped capabilities.
- Apply CPU/memory limits and other baseline pod constraints.
- Add verification test/assertions against staged runtime manifests.
- Exit gate: runtime launches always include baseline security constraints.

### Day 6: P0-E4-T5 Default-deny egress
- Add namespace/pod network policy for deny-by-default egress.
- Explicitly allow only required destinations.
- Validate denied paths (DB, secrets/admin APIs) and at least one allowed path.
- Exit gate: runtime network behavior matches isolation policy.

### Day 7: Hardening + verification sweep
- Run full tests and targeted failure drills.
- Add/clean runbooks and operator notes for reconcile/expiry/cleanup.
- Capture known gaps and next-step backlog notes.
- Exit gate: stable green build + documented operational behavior.

## Per-ticket Definition of Done
- Functional implementation complete.
- Unit/integration tests for acceptance cases added.
- Structured logs for operator diagnosis included.
- No direct lifecycle state edits outside transition service.
- Docs updated (execution notes + any runbook deltas).

## Immediate Follow-on (after this chunk)
1. Epic 6: Trace pipeline and replay
2. Epic 8: Authentication and authorization
3. Epic 9: Quota and abuse controls

## Scope Guardrails
Include now:
- Lifecycle correctness under runtime drift/failure
- Runtime teardown and isolation baseline

Defer until next phase:
- Full trace durability/replay protocol completion
- Production auth provider integration
- Quota/admission/rate-limiting controls
