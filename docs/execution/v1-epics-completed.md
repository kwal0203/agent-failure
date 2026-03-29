# V1 Epics and Tickets Completed

## Completed Tickets

### Session Lifecycle and Control Plane Foundation

- P0-E1-T1: Create session lifecycle schema COMPLETE (baseline)
- P0-E1-T2: Implement lifecycle transition service COMPLETE (baseline)
- P0-E1-T3: Implement idempotent session creation path COMPLETE (baseline, may evolve with lab/version source-of-truth refinements)
- P0-E1-T4: Implement session metadata endpoint COMPLETE (baseline)
- P0-E1-T5: Implement session reconciliation job COMPLETE
- P0-E1-T6: Implement session expiry job COMPLETE

### Learner UI Vertical Slice

- P1-E2-T1: Build demo app shell (auth deferred) COMPLETE
- P1-E2-T2: Build lab catalog page COMPLETE
- E2-T3: Build session page scaffold COMPLETE (intermediate visual learner UI milestone)
- E2-T4: Implement live prompt composer COMPLETE (intermediate visual learner UI milestone)
- E2-T5: Render streamed model output COMPLETE (intermediate visual learner UI milestone)
- E2-T6: Render session status and runtime sub-state COMPLETE (intermediate visual learner UI milestone)
- E2-T9: Add denial/error state handling COMPLETE (intermediate visual learner UI milestone)

### Live Session Streaming

- P0-E3-T1: Implement WebSocket session manager COMPLETE (baseline)
- P0-E3-T2: Implement USER_PROMPT handling COMPLETE (baseline)
- P0-E3-T3: Emit typed stream messages COMPLETE (baseline)

### Sandbox Runtime and Orchestration

- P0-E4-T1 / P0-E4-T2 / P0-E4-T3: Move from local path to staging runtimes COMPLETE (staging-equivalent baseline, with documented follow-on hardening/atomicity/readiness work)
- P0-E4-T4: Apply baseline runtime security profile COMPLETE
- P0-E4-T5: Apply default-deny egress policy COMPLETE
- P0-E4-T6: Implement runtime cleanup and teardown COMPLETE

### Agent Harness and Tool Execution

- P0-E5-T1: Build Agent Harness session loop COMPLETE (baseline)
- P0-E5-T2: Integrate model gateway provider COMPLETE (baseline)

### P2 Demo API and Runtime Slice

- P2-EA-T1: Implement `GET /api/v1/labs` catalog endpoint COMPLETE
- P2-EA-T2: Wire frontend lab catalog to backend endpoint COMPLETE
- P2-EA-T3: Deliver runnable prompt-injection runtime slice COMPLETE
- P2-EA-T4: Session launch/stream health hardening for demo reliability COMPLETE

### Trace Persistence for Evaluator Inputs

- P1-E6-T1: Implement canonical trace-event envelope COMPLETE (MVP baseline; post-MVP hardening deferred)
- P1-E6-T3: Persist lifecycle and learner events COMPLETE
- P1-E6-T4: Persist runtime and tool events COMPLETE

### Evaluator Baseline and Feedback

- P1-E7-T1: Define evaluator worker entrypoint COMPLETE
- P1-E7-T2: Implement evaluator idempotency keys COMPLETE
- P1-E7-T3: Implement initial constraint bundle for V1 labs COMPLETE
- P1-E7-T4: Persist evaluation outputs COMPLETE
- P1-E7-T5: Publish learner-visible feedback events COMPLETE

### Minimal Learner Feedback Surface

- P2-ED-T1: Add minimal feedback panel to session UI COMPLETE
