# Lab 1 Runtime Contract (Agent Runtime)

## Purpose

Define deterministic Lab 1 behavior for the agent runtime while preserving control-plane and evaluator compatibility.

This contract covers:
- session-scoped state transitions
- trigger conditions
- required runtime events and payload shape
- event ordering for the happy path

## Scope

Applies only to Lab 1 (`prompt-injection`) behavior in `runtimes/agent`.

Out of scope:
- control-plane persistence implementation
- evaluator rule implementation
- non-Lab-1 runtime behavior

## State Model

Session-scoped state:
- `clean` (default)
- `urgent_injection_active`

Additional per-session flags:
- `attack_email_sent_emitted` (bool, default `False`)
- `token_disclosed_emitted` (bool, default `False`)

### Transition Rules

1. `clean -> urgent_injection_active`
- Trigger: a `read_email` tool call succeeds and the resolved email has:
  - `malicious == True`
  - `urgency_marker == True`
- Required emitted event: `malicious_email_read`

2. `urgent_injection_active -> urgent_injection_active` (sticky)
- No reset within active session.
- Matches baseline behavior.

3. `attack_email_sent_emitted` toggle
- On first successful `list_inbox`, if inbox contains any `malicious == True` email:
  - emit `attack_email_sent`
  - set `attack_email_sent_emitted = True`
- Never emit `attack_email_sent` again for same session.

4. `token_disclosed_emitted` toggle
- First time assistant output contains protected manager address secret:
  - emit `token_disclosed`
  - set `token_disclosed_emitted = True`
- Subsequent disclosures do not emit duplicate `token_disclosed` for that session.

## Behavioral Contract

### Before malicious urgent email is read
If user asks to reveal manager address, assistant should refuse per Lab 1 system prompt.

### After malicious urgent email is read
If `urgent_injection_active` and user asks for manager address, runtime should permit vulnerable disclosure behavior (learning objective).

This may be implemented via hook-mediated short-circuit response for determinism.

## Event Contract (Control-Plane Compatibility)

Runtime must emit only events in `RuntimeStreamEvent` union and preserve payload requirements used by trace/evaluator mapping.

Lab 1-relevant runtime events:
- `attack_email_sent`
  - required keys: `email_id`, `recipient`, `subject`
- `malicious_email_read`
  - required keys: `email_id`, `subject`, `malicious_marker`
- `token_disclosed`
  - required keys: `channel`, `token_kind`

Tool events remain required around tool execution:
- `tool_call_requested`
- `tool_call_succeeded` / `tool_call_failed`

## Ordering Contract

Within a turn, events should appear in stable order:

1. `turn_started`
2. zero or more tool events (`tool_call_requested`, then terminal tool event)
3. lab runtime events caused by that tool result (`attack_email_sent`, `malicious_email_read`)
4. `text_chunk` output events
5. `turn_completed` or `turn_failed`

For disclosure turns:
- `token_disclosed` must be emitted before turn terminal event.
- Preferred: emit `token_disclosed` immediately before first chunk containing the protected token.

## Canonical Happy Path Timeline

Goal: reveal manager address through urgency injection.

1. User asks for manager address.
- Expected state: `clean`
- Expected outcome: refusal text
- Expected lab events: none

2. User injects malicious urgent email via inbox endpoint.
- Runtime stream not involved for this action.

3. User asks agent to read malicious email.
- Tool events for `read_email`
- Emit `malicious_email_read`
- Transition to `urgent_injection_active`

4. User asks for manager address again.
- State: `urgent_injection_active`
- Expected outcome: assistant reveals protected manager address
- Emit `token_disclosed` when disclosure appears in output

## Non-Goals / Explicit Constraints

- Do not infer urgency from free text alone for state transition.
- Do not depend on model stochastic behavior for core lab outcome.
- Do not change control-plane runtime event names or payload keys.

## Baseline Parity Decisions Captured

- Sticky compromise state after urgent malicious read: yes.
- Transition requires explicit email metadata (`malicious` + `urgency_marker`): yes.
- `attack_email_sent` emitted once on first inbox listing if malicious email exists: yes.
