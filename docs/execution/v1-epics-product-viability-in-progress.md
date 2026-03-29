# P1 Product Viability

This file tracks tickets deferred/skipped during the P0 backlog implementation sprint and explicitly prioritized for the P1 product viability sprint.

## Scope

- Epic 2: Learner UI Vertical Slice
- Epic 6: Trace Pipeline and Replay
- Epic 7: Evaluator and Feedback Pipeline

---

# Epic 2: Learner UI Vertical Slice

**Goal:** Deliver the first end-to-end learner experience for lab selection, live interaction, and session review.

## Tickets

### E2-T7: Build history view

- Render persisted learner-visible message history and feedback.
- Link to: API and WebSocket Contract Spec

### E2-T8: Build trace viewer

- Render ordered learner-visible trace events with pagination.
- Link to: Trace Event Schema and Evaluator Contract Spec

---

# Epic 6: Trace Pipeline and Replay

**Goal:** Persist ordered durable trace events and support replay for learners, operators, and evaluators.

## Tickets

### E6-T2: Assign session-scoped event ordering

- Guarantee monotonically increasing event\_index within a session.
- Link to: Trace Event Schema and Evaluator Contract Spec

### E6-T5: Implement learner-visible event filtering

- Separate learner-visible and internal/admin-only trace projections.
- Link to: Trace Event Schema and Evaluator Contract Spec

### E6-T6: Implement replay cursor/pagination logic

- Support stable replay and retrieval of trace history.
- Link to: API and WebSocket Contract Spec

### E6-T7: Add trace schema validation tests

- Ensure emitted events conform to the required envelope and event-family semantics.
- Link to: Trace Event Schema and Evaluator Contract Spec

---

# Epic 7: Evaluator and Feedback Pipeline

**Goal:** Turn committed trace events into constraint-based feedback and durable evaluation outcomes.

## Tickets

### E7-T6: Support terminal-outcome handoff

- Allow evaluator-detected terminal outcomes to be consumed by the Control Plane for session completion.
- Link to: Trace Event Schema and Evaluator Contract Spec

### E7-T7: Add evaluator correctness tests

- Verify evaluator uses committed events only and correct lab version binding.
- Link to: Trace Event Schema and Evaluator Contract Spec
