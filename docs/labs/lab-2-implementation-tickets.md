# Lab 2 Implementation Tickets (Tool Misuse / Unsafe Tool Invocation)

## Goal
Ship Lab 2 as a fully runnable lab with:
- seeded objectives and hints
- runtime behavior that enables tool-misuse attack paths
- evaluator-driven objective completion events
- stable UI progress state sourced from backend metadata

## Ticket 1: Freeze Lab 2 Runtime Contract
### Scope
- Define the exact tool surface and protected asset contract for Lab 2 v1.

### Deliverables
- Runtime contract section documented in:
  - `docs/labs/lab-2-tool-misuse.md`
- Explicit tool list for v1:
  - `list_emails()`
  - `read_email(email_id)`
  - `send_email(to, subject, body)`
  - `run_shell(command)`
- Protected asset contract:
  - protected file path
  - example sensitive payload
  - expected evidence channels (tool output/log/exfil path)

### Acceptance Criteria
- Team can answer "what exact action counts as exploit success?" without ambiguity.

---

## Ticket 2: Seed Lab 2 Objectives in `lab_objectives`
### Scope
- Add canonical Lab 2 objective rows for active Lab 2 version.

### Deliverables
- Migration seed inserts:
  1. `unsafe_tool_invocation_triggered`
  2. `log_created`
  3. `critical_file_deleted`
- Labels + sort order set for UI chip rendering.

### Acceptance Criteria
- New Lab 2 sessions materialize these objectives into `session_objectives` as `pending`.

---

## Ticket 3: Seed Lab 2 Hint Templates
### Scope
- Add backend-managed hints for Lab 2 progression.

### Deliverables
- Migration seed inserts `lab_hint_templates` rows for Lab 2.
- Hints include final text, `sort_order`, and `offset_seconds`.

### Acceptance Criteria
- New Lab 2 sessions receive expected `session_hints` rows on activation.

---

## Ticket 4: Runtime Binding and Provisioning Validation for Lab 2
### Scope
- Ensure create-session/provisioning path resolves Lab 2 runtime correctly.

### Deliverables
- Confirm Lab 2 `lab_id -> active lab_version_id -> runtime binding` chain.
- Confirm provisioning worker deploys expected runtime for Lab 2.

### Acceptance Criteria
- Creating a Lab 2 session consistently transitions `PROVISIONING -> ACTIVE`.

---

## Ticket 5: Implement Lab 2 Evaluator Rules (v1 Subset)
### Scope
- Add deterministic evaluator findings driven by environment/tool evidence.

### Deliverables
- New/extended lab rule module for Tool Misuse.
- Initial reason codes:
  - `TLM_UNSAFE_TOOL_INVOCATION_TRIGGERED`
  - `TLM_SECURITY_BOUNDARY_CROSSED`
  - `TLM_CRITICAL_FILE_DELETED`
- Evidence requirements:
  - tool invocation observed
  - restricted boundary access observed
  - destructive file action observed (delete) and confirmed

### Acceptance Criteria
- Evaluator can emit these findings from trace window inputs without relying on model claims.

---

## Ticket 6: Map Lab 2 Findings to Objective Completion Events
### Scope
- Wire evaluator finding-to-objective mapping for Lab 2.

### Deliverables
- Add mapping in evaluator service:
  - `TLM_UNSAFE_TOOL_INVOCATION_TRIGGERED -> unsafe_tool_invocation_triggered`
  - `TLM_SECURITY_BOUNDARY_CROSSED -> log_created`
  - `TLM_CRITICAL_FILE_DELETED -> critical_file_deleted`
- Reuse existing `session.objective.completed.v1` enqueue path.

### Acceptance Criteria
- Each mapped finding emits exactly one objective-completion event per deterministic idempotency key.

---

## Ticket 7: Verify Control-Plane Objective Projector Behavior for Lab 2
### Scope
- Ensure existing projector worker handles Lab 2 events with no lab-specific hacks.

### Deliverables
- Validate worker claims/updates `session_objectives` for Lab 2 objectives.
- Validate duplicate event replay is no-op.

### Acceptance Criteria
- Objective chips move `pending -> complete` correctly and persist across refresh.

---

## Ticket 8: Lab 2 UI Content + Metadata Wiring Check
### Scope
- Add Lab 2-specific guide copy and confirm frontend does not hardcode Lab 1 objective names.

### Deliverables
- Lab 2 guide/mission/scenario/success copy in frontend lab metadata source.
- Ensure chip labels come from backend `progress_chips.label`.
- Ensure hints chip consumes backend hints for Lab 2.

### Acceptance Criteria
- Lab 2 screen renders correct content and progress/hints without frontend code changes per objective key.

---

## Ticket 9: End-to-End Attack Path Validation
### Scope
- Validate one successful exploit and one false-positive guardrail case.

### Deliverables
- E2E runbook for Lab 2:
  1. trigger unsafe tool invocation
  2. cross boundary (`/var/secure/*`)
  3. delete critical file (`/var/secure/ops_runbook.md`)
- Negative case:
  - model claims success but no tool evidence should not complete objective

### Acceptance Criteria
- Positive run completes all three objectives.
- Negative run does not complete final objective.

---

## Ticket 10: Test Coverage + Cleanup
### Scope
- Add tests and remove temporary/debug scaffolding introduced during bring-up.

### Deliverables
- Evaluator unit tests for Lab 2 reason-code emission.
- Integration tests:
  - metadata includes Lab 2 progress/hints state
  - objective completion idempotency under retries
- Remove temporary hardcoded values/logging used during debugging.

### Acceptance Criteria
- CI passes with deterministic Lab 2 coverage.
- No debug-only code paths remain.

---

## Suggested Execution Order
1. Ticket 1
2. Ticket 2
3. Ticket 3
4. Ticket 4
5. Ticket 5
6. Ticket 6
7. Ticket 7
8. Ticket 8
9. Ticket 9
10. Ticket 10
