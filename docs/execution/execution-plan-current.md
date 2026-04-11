# UI Execution Plan (Next 2 Days)

## Objective
Ship a high-impact UI polish pass in 2 days: better visual identity, clearer learning flow, and smoother interaction quality.

## Plan
1. Lock scope (1-2 hours)
- Choose 3 core screens only: `LabsPage`, active lab workspace (attacker/victim/trace), feedback panel.
- Define “awesome” criteria: clarity, speed, delight, zero confusion in primary flow.
- Freeze non-UI backend work for this sprint.

2. Design system pass (Day 1 morning)
- Create a small visual system: typography, spacing scale, color tokens, panel styles.
- Add reusable primitives: card shell, section header, badge/chip, timeline row, callout.
- Standardize interaction states: hover, focus, loading, empty, error.

3. Workflow UX pass (Day 1 afternoon)
- Rework lab workspace layout for readability:
  - Attacker console feels tool-like.
  - Victim chat feels conversation-like.
  - Trace panel feels debug timeline-like.
- Improve hierarchy and affordance for next action (what learner should do now).
- Add clean empty states and skeleton loaders.

4. Motion + responsiveness (Day 2 morning)
- Add restrained motion: panel entrance, streaming reveal, trace event appearance.
- Ensure mobile/tablet usability for the same screens.
- Fix spacing/overflow/scroll issues in split-pane layout.

5. Polish + QA + demo prep (Day 2 afternoon)
- Visual polish sweep (spacing, alignment, copy tone consistency).
- Accessibility quick pass: keyboard focus, contrast, aria labels on critical controls.
- Performance quick pass: avoid unnecessary rerenders in chat/trace lists.
- Record/demo checklist: 1 smooth path from inject -> chat -> trace -> feedback.

## Concrete Deliverables (End of Day 2)
1. Updated UI tokens and shared components.
2. Refined `LabsPage` and primary lab workspace.
3. Improved feedback/trace visual semantics.
4. Responsive behavior verified on desktop + mobile widths.
5. Demo-ready flow with no visual blockers.
