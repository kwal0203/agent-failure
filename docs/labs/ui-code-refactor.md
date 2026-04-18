# SessionPage UI Refactor Plan

## Goal
Break `apps/frontend/src/pages/SessionPage.tsx` into focused modules with clear ownership, while preserving behavior and test coverage.

## Target Structure
- `pages/session/SessionPageContainer.tsx` (or keep `SessionPage.tsx` as thin orchestrator, ~150-250 lines)
- `pages/session/hooks/useSessionData.ts`
- `pages/session/hooks/useTranscriptStreamView.ts`
- `pages/session/hooks/useHintsState.ts`
- `pages/session/hooks/useSessionActions.ts`
- `pages/session/components/SessionHeaderStatus.tsx`
- `pages/session/components/SessionHintsPopover.tsx`
- `pages/session/constants.ts`
- `pages/session/styles.ts` (chip tone/style helpers)

## Incremental Refactor Plan

### 1. Stabilize behavior baseline
- Add focused tests for:
  - transcript internal scroll + jump-to-latest
  - right timeline internal scroll behavior
  - status chips + hints unlock/popover
- Goal: lock current expected behavior before moving code.

### 2. Extract constants + pure helpers (zero behavior change)
- Move:
  - hint catalog/schedule
  - tone helpers (`agentStatusTone`, `objectiveTone`, `hintTone`, `statusChipStyle`)
  - simple formatting helpers
- `SessionPage` should still work with no logic change.

### 3. Extract header UI
- Create `SessionHeaderStatus.tsx` for:
  - progress chips
  - agent/session chips
  - hints chip + popover rendering
- `SessionPage` passes props only.
- This removes a large JSX block and isolates layout churn from data logic.

### 4. Extract hints state machine
- `useHintsState.ts` handles:
  - unlock timing
  - unread state
  - panel open/close
  - reset on session change
- Keep append-to-timeline callback injection as dependency.

### 5. Extract transcript streaming/render state logic
- `useTranscriptStreamView.ts` handles:
  - chunk buffering/reveal animation
  - active entry/finalization
  - jump-to-latest state
  - transcript scroll tracking
- This is currently the densest complexity.

### 6. Extract data/event ingestion
- `useSessionData.ts` handles:
  - metadata polling
  - evaluator feedback polling
  - stream message ingestion + timeline mapping
  - progress-state updates
- Keep side effects centralized and easier to debug.

### 7. Extract user actions
- `useSessionActions.ts` for:
  - send prompt
  - inject email
  - reset email
  - tool-select behavior
- Makes async action/error handling testable independently.

### 8. Final cleanup + naming pass
- Remove dead state/refs.
- Enforce single responsibility of each hook/component.
- Keep `SessionPage.tsx` as an orchestrator wiring hooks to components.

## Acceptance Criteria
- `SessionPage.tsx` reduced from ~1000 lines to ~200 lines.
- No behavior regressions in:
  - transcript scroll/jump
  - right timeline scroll
  - hints unlock/popover
  - chip state updates
- All checks pass:
  - `biome:check`
  - `typecheck`
  - `test`

## Suggested Execution Pattern
- Do refactor in small, reviewable commits aligned to each step above.
- Run `biome`, `typecheck`, and `test` after each step.
- Avoid mixing behavior fixes with structural refactors in the same commit unless required.
