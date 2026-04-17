# UI Implementation Tickets: Lab 1 Workspace

Source specs:
- `docs/labs/ui-spec.md`
- `docs/labs/lab-1-prompt-injection-poison-inbox.md`

This backlog is ordered for incremental delivery and testing.

## Ticket 1: Extract Session Workspace Scaffold
Status: `done`

### Scope
- Refactor `SessionPage` into composable sections without changing behavior:
  - `LabGuideColumn`
  - `WorkspaceColumn`
  - `FeedbackColumn`
- Introduce a page-level workspace state object to prepare for tool-pane and timeline behavior.
- Preserve all current user-visible behavior and existing API calls.

### Acceptance Criteria
- Existing Session page behavior remains unchanged.
- Existing tests for `SessionPage` pass without functional regressions.

### Validation
- `cd apps/frontend && npm test`

### Implementation Notes
- Extracted page sections into:
  - `apps/frontend/src/pages/session/components/LabGuideColumn.tsx`
  - `apps/frontend/src/pages/session/components/WorkspaceColumn.tsx`
  - `apps/frontend/src/pages/session/components/FeedbackColumn.tsx`
- Added shared session UI/types modules:
  - `apps/frontend/src/pages/session/types.ts`
  - `apps/frontend/src/pages/session/ui.ts`
- Updated `apps/frontend/src/pages/SessionPage.tsx` to compose these sections and added page-level `SessionWorkspaceState` scaffolding.
- Validation run:
  - `cd apps/frontend && npm test` (pass)
  - `cd apps/frontend && npm run typecheck` (pass)

---

## Ticket 2: Implement 3-Column Full-Height App Shell
Status: `done`

### Scope
- Implement desktop-first 3-column layout (left guide, center workspace, right feedback).
- Make app fill viewport height and prevent full-page scrolling during normal use.
- Ensure each column has internal overflow handling.
- Keep center column as widest.

### Acceptance Criteria
- Page no longer relies on full-page vertical scroll for normal session use.
- Left, center, and right columns are visible and independently scrollable where needed.

### Validation
- Manual: Open Session page on desktop and confirm internal panel scrolling.
- `cd apps/frontend && npm test`

### Implementation Notes
- Updated `apps/frontend/src/pages/SessionPage.tsx` to a desktop 3-column grid app shell:
  - full-height viewport container (`height: 100vh`, overflow hidden)
  - grid columns sized as `minmax(280px, 24%) minmax(520px, 1fr) minmax(300px, 28%)`
  - left and right columns are independently scrollable (`overflowY: auto`)
  - center column is constrained and non-scrolling at page level (`minWidth: 0`, `overflow: hidden`)
- Updated `apps/frontend/src/pages/session/components/WorkspaceColumn.tsx` to use a full-height flex column:
  - transcript section is the scrollable region (`flex: 1`, `minHeight: 0`, `overflowY: auto`)
  - prompt/composer section remains fixed at bottom (`flex: 0 0 auto`)
- Validation run:
  - `cd apps/frontend && npm run biome:check` (pass)
  - `cd apps/frontend && npm test` (pass)
  - `cd apps/frontend && npm run typecheck` (pass)

---

## Ticket 3: Build Left Lab Guide (Mission-First)
Status: `done`

### Scope
- Add left-column guide cards/sections:
  - Lab header (title, difficulty, optional ETA)
  - Mission
  - Scenario
  - Success criteria
  - Recommended steps
  - Hints (collapsed/progressive)
  - Learning objective / Why this matters
- Ensure mission and success criteria are near the top.

### Acceptance Criteria
- Required labels are present and explicit.
- Mission and success criteria are visible without whole-page scroll.
- Hints are progressively disclosed (not all shown by default).

### Validation
- Add/extend component tests for required labels.
- Manual visual check for placement.
- `cd apps/frontend && npm test`

### Implementation Notes
- Updated `apps/frontend/src/pages/session/components/LabGuideColumn.tsx` to add mission-first guide sections:
  - `Lab Guide` header (title, difficulty, estimated time)
  - `Mission`
  - `Scenario`
  - `Success Criteria`
  - `Recommended Steps`
  - `Hints` (collapsed by default using `<details>`, with progressive hint reveal button)
  - `Why This Matters`
- Kept attacker email functionality intact in the left column under `Attack Tools`.
- Added test coverage in `apps/frontend/src/pages/SessionPage.test.tsx` for required guide labels and progressive hint reveal behavior.
- Validation run:
  - `cd apps/frontend && npm run biome:check` (pass)
  - `cd apps/frontend && npm test` (pass)
  - `cd apps/frontend && npm run typecheck` (pass)

---

## Ticket 4: Tool Strip + Expandable Tool Pane Mechanics
Status: `done`

### Scope
- Build tool strip with 5 initial tools: Email, Files, Payloads, Notes, Recon.
- Tool interaction model:
  - Click closed tool: open pane and select tool.
  - Click active tool: collapse pane.
  - Click different tool: switch content without collapse-reset.
- Add smooth expand/collapse animation.

### Acceptance Criteria
- Tool pane follows open/close/switch behavior exactly.
- Transcript remains visible while a tool is open.
- Tool strip remains visible while pane is open.

### Validation
- Add state transition tests for open/close/switch.
- Manual behavior walkthrough.
- `cd apps/frontend && npm test`

### Implementation Notes
- Implemented top-of-center-column tool strip and expandable pane in:
  - `apps/frontend/src/pages/session/components/WorkspaceColumn.tsx`
- Added 5 tools with toggle/switch behavior:
  - `Email`, `Files`, `Payloads`, `Notes`, `Recon`
- Implemented interaction rules:
  - clicking closed tool opens pane and selects tool
  - clicking active tool collapses pane
  - clicking a different tool switches pane content without collapsing first
- Added smooth pane transition (max-height/opacity/padding/margin transitions) and kept transcript visible below the pane at all times.
- Updated workspace state in:
  - `apps/frontend/src/pages/SessionPage.tsx`
  - `apps/frontend/src/pages/session/types.ts`
- Added behavior test coverage for open/close/switch flows:
  - `apps/frontend/src/pages/SessionPage.test.tsx`
- Validation run:
  - `cd apps/frontend && npm run biome:check` (pass)
  - `cd apps/frontend && npm test` (pass)
  - `cd apps/frontend && npm run typecheck` (pass)

---

## Ticket 5: Move Email Attacker Form into Tool Pane with Persistent State
Status: `done`

### Scope
- Move attacker email form into `EmailToolForm` inside tool pane.
- Preserve unsent form values while session is active and across tool switches.
- Add explicit `Reset` action.
- Keep inject endpoint integration unchanged.

### Acceptance Criteria
- Email injection still works via existing API contract.
- Switching tools does not clear unsent email draft.
- Reset explicitly clears email form state.

### Validation
- Update existing inject-email test to new UI location.
- Add persistence/reset tests.
- `cd apps/frontend && npm test`

### Implementation Notes
- Moved email injection form out of the left guide and into the center-column `Email` tool pane:
  - Added `apps/frontend/src/pages/session/components/EmailToolForm.tsx`
  - Integrated into `apps/frontend/src/pages/session/components/WorkspaceColumn.tsx`
- Kept email submission contract unchanged (`POST /api/v1/sessions/:id/inbox/email` with existing payload).
- Preserved unsent draft state across tool switches by keeping form state in `SessionPage`.
- Added explicit `Reset` button that clears `from`, `subject`, `body`, malicious toggle, and transient result/error messages.
- Simplified left `Attack Tools` guide section to point users to the center tool strip.
- Updated and added tests in `apps/frontend/src/pages/SessionPage.test.tsx`:
  - inject-email flow now opens `Email` tool pane first
  - new test verifies draft persistence across tool switches and reset behavior
- Validation run:
  - `cd apps/frontend && npm run biome:check` (pass)
  - `cd apps/frontend && npm test` (pass)
  - `cd apps/frontend && npm run typecheck` (pass)

---

## Ticket 6: Transcript + Composer Behavior Hardening
Status: `done`

### Scope
- Ensure transcript occupies remaining center-column space.
- Keep composer pinned and always visible.
- Implement smart autoscroll:
  - Auto-scroll when user is near bottom.
  - Do not force scroll when user has scrolled up.
  - Show `Jump to latest` affordance when new messages arrive off-screen.
- Preserve transcript scroll position while tool pane opens/closes.

### Acceptance Criteria
- Composer remains visible at all times on desktop.
- Transcript behavior matches autoscroll rules.
- Tool-pane transitions do not reset transcript reading position.

### Validation
- Add tests for autoscroll/jump behavior.
- Manual streaming test while scrolled up.
- `cd apps/frontend && npm test`

### Implementation Notes
- Implemented smart transcript scrolling behavior in `apps/frontend/src/pages/SessionPage.tsx`:
  - near-bottom detection on transcript scroll (`<= 48px`)
  - auto-scroll only when `transcriptAutoScrollEnabled` is true
  - when scrolled up, new transcript content no longer forces scroll
  - added `Jump to latest` control state and handler
- Updated `apps/frontend/src/pages/session/components/WorkspaceColumn.tsx`:
  - transcript viewport now emits scroll events to parent logic
  - added sticky `Jump to latest` button in transcript region
  - composer remains fixed at bottom of the center workspace
- Added test coverage in `apps/frontend/src/pages/SessionPage.test.tsx`:
  - `Jump to latest` appears when user is scrolled up and new transcript content arrives
  - transcript scroll position remains stable when tool pane opens/closes
- Validation run:
  - `cd apps/frontend && npm run biome:check` (pass)
  - `cd apps/frontend && npm test` (pass)
  - `cd apps/frontend && npm run typecheck` (pass)

---

## Ticket 7: Right Column Event Timeline + Filters + Explanations
Status: `done`

### Scope
- Build right-column event timeline cards with:
  - icon, title, short description, timestamp, type badge, expandable details
- Add filter chips:
  - event type: all, important, attacker actions, agent actions, tool calls, system, learning explanations
  - granularity: high-level, detailed, full trace
- Add distinct explanation card styling for educational interpretation.

### Acceptance Criteria
- Timeline updates without full page reload.
- Filtering updates visible events correctly.
- Explanation cards are visually distinct from ordinary events.

### Validation
- Add tests for filter behavior and timeline rendering.
- Manual check for live updates.
- `cd apps/frontend && npm test`

### Implementation Notes
- Expanded right column in `apps/frontend/src/pages/session/components/FeedbackColumn.tsx` to include:
  - event type filter chips (`All`, `Important`, `Attacker actions`, `Agent actions`, `Tool calls`, `System`, `Learning explanations`)
  - granularity chips (`High-level`, `Detailed`, `Full trace`)
  - pinned important events section
  - timeline card rendering with icon marker, title, description, timestamp/type badge, optional details
  - distinct explanation-card section
- Added timeline event model in `apps/frontend/src/pages/session/types.ts`:
  - `EventType`, `EventGranularity`, `TimelineEvent`
- Wired real-time timeline ingestion in `apps/frontend/src/pages/SessionPage.tsx`:
  - stream-driven events (`SESSION_STATUS`, final `AGENT_TEXT_CHUNK`, `POLICY_DENIAL`, `TRACE_EVENT`, `SYSTEM_ERROR`, `LEARNER_FEEDBACK`)
  - attacker action events on email injection success/failure
  - dedupe for timeline IDs and learner-feedback derived explanation events
- Added/updated tests in `apps/frontend/src/pages/SessionPage.test.tsx`:
  - timeline filtering by type and granularity
  - adjusted assertions for duplicated feedback text now shown in multiple timeline/feed surfaces
- Validation run:
  - `cd apps/frontend && npm run biome:check` (pass)
  - `cd apps/frontend && npm test` (pass)
  - `cd apps/frontend && npm run typecheck` (pass)

---

## Ticket 8: Status Summary + Objective Progress + Pinned Important Events
Status: `todo`

### Scope
- Add top-right status summary:
  - agent status
  - attack status
  - objectives completed
- Add objective progress card and pinned important events section.
- Ensure key events (first successful injection, policy violation, win condition) are pinnable/auto-pinned.

### Acceptance Criteria
- Status summary reflects current session state.
- Objective progress updates as learner actions occur.
- Important events remain visible/pinned even as timeline grows.

### Validation
- Add deterministic mapping tests from event/reason codes.
- Manual success-flow walkthrough.
- `cd apps/frontend && npm test`

---

## Ticket 9: Accessibility + Reduced Motion + Tablet Behavior
Status: `todo`

### Scope
- Ensure all controls are keyboard-accessible.
- Add accessible labels for icon-only controls.
- Ensure logical focus order across columns.
- Respect reduced-motion preferences for pane animations.
- Add tablet/narrow-desktop responsive behavior (collapsible side panels).

### Acceptance Criteria
- Core workflows can be completed keyboard-only.
- Reduced-motion mode disables/subdues non-essential animation.
- Tablet width preserves center workspace as primary interaction surface.

### Validation
- Manual keyboard walkthrough.
- Manual reduced-motion verification.
- `cd apps/frontend && npm test`

---

## Ticket 10: MVP Acceptance Sweep + Cleanup
Status: `todo`

### Scope
- Verify all UI-spec MVP acceptance criteria.
- Normalize copy/microcopy and panel labels.
- Remove dead styles and finalize structure.
- Document any known follow-ups.

### Acceptance Criteria
- All v1 MVP acceptance criteria from `ui-spec.md` are met.
- Frontend quality checks pass.

### Validation
- `cd apps/frontend && npm run typecheck`
- `cd apps/frontend && npm run lint`
- `cd apps/frontend && npm test`
- Manual end-to-end session walkthrough.

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

## Ticket Workflow Convention
For each ticket:
- Set status to `in_progress` when work starts.
- Add a short implementation note section with changed files.
- Set status to `done` only after validation commands pass.
