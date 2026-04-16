# UI Implementation Tickets: Lab 1 Workspace

Source specs:
- `docs/labs/ui-spec.md`
- `docs/labs/lab-1-prompt-injection-poison-inbox.md`

This backlog is ordered for incremental delivery and testing.

## Ticket 1: Extract Session Workspace Scaffold
Status: `todo`

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

---

## Ticket 2: Implement 3-Column Full-Height App Shell
Status: `todo`

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

---

## Ticket 3: Build Left Lab Guide (Mission-First)
Status: `todo`

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

---

## Ticket 4: Tool Strip + Expandable Tool Pane Mechanics
Status: `todo`

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

---

## Ticket 5: Move Email Attacker Form into Tool Pane with Persistent State
Status: `todo`

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

---

## Ticket 6: Transcript + Composer Behavior Hardening
Status: `todo`

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

---

## Ticket 7: Right Column Event Timeline + Filters + Explanations
Status: `todo`

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
