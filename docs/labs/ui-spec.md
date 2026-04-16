# **UI Spec: AI Agent Security Lab Workspace**

## **1\. Purpose**

This document specifies the desktop-first user interface for an educational AI agent security sandbox / cyber range. The UI must support three learner needs simultaneously:

1. **Orientation**: understand the lab goal, success criteria, and next steps.
2. **Action**: interact with the agent and attacker tools without losing context.
3. **Reflection**: observe what happened and why it matters.

The main design goal is to eliminate excessive vertical scrolling and make the lab understandable without instructor narration.

---

## **2\. Product Context**

The product teaches AI agent security attacks, beginning with labs such as indirect prompt injection, tool misuse, and risky code execution.

The existing UI contains:

* an attacker console (currently email-style form)
* a learner event box
* a transcript panel
* a user message box

Problems identified from feedback:

* users do not immediately understand the task
* learner feedback lacks clear placement and purpose
* the current vertical stack requires too much scrolling
* educational steps and explanations are not visible enough

---

## **3\. Design Principles**

The UI should follow these principles:

1. **Persistent mission visibility**: the learner should always be able to see what they are trying to do.
2. **Preserve context while acting**: tools should open without hiding the transcript.
3. **Progressive disclosure**: show the minimum needed by default, with more detail available when requested. This matches established UX guidance for complex applications and training-oriented interfaces. ([nngroup.com](https://www.nngroup.com/articles/progressive-disclosure/?utm_source=chatgpt.com))
4. **Clear visual hierarchy**: the most important elements should be visually dominant and easy to scan. ([nngroup.com](https://www.nngroup.com/articles/visual-hierarchy-ux-definition/?utm_source=chatgpt.com))
5. **Educational feedback, not just system logging**: the UI should explain important events, not merely report them.
6. **Minimize page scrolling**: panels should scroll internally where appropriate.

---

## **4\. Desktop Layout Overview**

Use a **3-column desktop layout**.

### **Left Column: Lab Guide**

Purpose: orient the learner.

Contents:

* lab title
* difficulty
* scenario summary
* mission / objective
* success criteria
* recommended steps
* hint section (expandable)
* key concept / learning objective

### **Center Column: Active Workspace**

Purpose: let the learner perform actions and maintain awareness of the live conversation.

Contents from top to bottom:

1. tool strip
2. expandable tool pane
3. transcript
4. message composer

### **Right Column: Feedback and Progress**

Purpose: help the learner interpret what happened.

Contents:

* status summary
* objective progress
* filter controls
* event timeline
* explanation cards for important events

---

## **5\. Layout Sizing Rules**

These are desktop-first guidelines, not hard-coded absolute values.

### **Overall page**

* App should fill the viewport height.
* The page itself should ideally not scroll during normal use.
* Each main column should manage its own internal overflow.

### **Column widths**

Suggested starting proportions:

* Left column: 22% to 26%
* Center column: 44% to 52%
* Right column: 24% to 30%

The center column should be the widest column.

### **Center column vertical structure**

Default state:

* tool strip: \~48 to 64 px height
* expandable tool pane: collapsed (0 height or hidden)
* transcript: fills remaining space
* composer: fixed at bottom

Tool-open state:

* tool strip remains fixed height
* tool pane expands below the strip
* tool pane target height: \~220 to 320 px, or roughly 25% to 35% of center-column height
* transcript shrinks to take remaining space
* composer remains fixed at bottom

Important rule:

* the transcript must remain visible whenever a tool is open
* tools must not replace the transcript with a full modal in the default workflow

---

## **6\. Component Specification**

## **6.1 Left Column: Lab Guide**

The lab guide is always visible on desktop.

### **Required sections**

1. **Lab Header**
   * lab title
   * difficulty badge
   * optional estimated time
2. **Mission**
   * one-sentence description of the learner’s goal
   * must be visible without scrolling if possible
3. **Scenario**
   * short narrative about the environment and what the learner is interacting with
4. **Success Criteria**
   * explicit win condition(s)
   * examples:
     * convince the agent to follow malicious instructions
     * trigger unsafe tool usage
     * recover protected information
5. **Recommended Steps**
   * short ordered list
   * should guide the learner without forcing a wizard flow
6. **Hints**
   * hidden by default or collapsed
   * presented in a hint ladder:
     * Hint 1: broad nudge
     * Hint 2: more specific
     * Hint 3: near-explicit guidance
7. **Learning Objective / Why This Matters**
   * short explanation of the security concept being taught

### **Behavior**

* Left column may scroll internally if content exceeds available height.
* Mission and success criteria should appear near the top.
* Hints should be progressively disclosed, not all shown at once.

---

## **6.2 Center Column: Tool Strip**

This is the top control surface for attacker tools.

### **Structure**

* horizontal row of tools
* recommended: icon \+ short text label
* if labels are hidden for space reasons, tooltips are mandatory

### **Initial tools**

Suggested initial tools:

* Email
* Files
* Payloads
* Notes
* Recon

Actual tool set can vary; the UI pattern should support 5 tools initially.

### **Behavior**

* clicking a tool opens the expandable tool pane below the strip
* clicking the active tool again collapses the pane
* clicking a different tool switches the pane content without a full layout reset
* tool state should persist unless explicitly reset by the user

### **Design constraints**

* do not use a blocking modal dialog for core recurring attacker actions such as composing an email
* the tool strip must remain visible while a tool is open

---

## **6.3 Center Column: Expandable Tool Pane**

This is the main place where a selected attacker tool is used.

### **Primary interaction model**

When a tool is selected:

* the pane expands downward below the tool strip
* the transcript is pushed downward and resized
* the transcript remains visible

### **Primary reasons for this pattern**

* preserves awareness of the current transcript
* keeps the learner in the same workspace
* avoids the context loss caused by modal dialogs

### **Email tool requirements**

For the initial email attacker tool, include:

* From field
* Subject field
* Body textarea
* Send button
* Reset button
* optional Load Example / Template button
* optional minimization / collapse control

### **Pane behavior**

* expansion and collapse should be animated smoothly
* transcript scroll position must be preserved when opening or closing the pane
* unsent form data must persist while the session is active unless the user clicks Reset

### **Height constraints**

* pane should not exceed roughly one third of center-column height in normal desktop mode
* if tool content exceeds the pane height, the pane itself scrolls internally

---

## **6.4 Center Column: Transcript**

The transcript is the primary persistent context display.

### **Content**

* user messages
* agent responses
* optionally system messages, visually distinguished from normal chat

### **Behavior**

* transcript occupies the remaining vertical space between the tool pane and the composer
* transcript scrolls internally when content exceeds available space
* transcript should auto-scroll to latest messages during active interaction unless the user has manually scrolled upward
* if user is reading older content, do not forcibly snap them to the bottom

### **Visual treatment**

* chat-like layout is preferred over a raw log view
* user and agent messages should be visually distinguishable
* system messages should be visually lighter or otherwise separated

---

## **6.5 Center Column: Message Composer**

This is the learner’s persistent chat input for interacting directly with the agent.

### **Placement**

* fixed at the bottom of the center column
* always visible on desktop

### **Contents**

* text input / textarea
* send button
* optional shortcut hint

### **Behavior**

* remains visible whether or not a tool pane is open
* should not be pushed off-screen during normal use

---

## **6.6 Right Column: Feedback and Progress**

This column should function as a structured learning-aware activity timeline.

### **Top section: status summary**

Include compact glanceable items such as:

* agent status (idle / processing / acted)
* attack status (no effect / partial / success)
* objectives completed (e.g. 1/3)

### **Filter controls**

The event stream should support filtering by:

1. **Event type**
   * all
   * important
   * attacker actions
   * agent actions
   * tool calls
   * system
   * learning explanations
2. **Granularity**
   * high-level
   * detailed
   * full trace

Quick filter chips are preferred for v1.

### **Event timeline**

Each event should be displayed as a compact timeline card rather than a raw log line.

Each event card should support:

* icon
* title
* short description
* timestamp
* type badge
* optional expandable details

### **Explanation cards**

For important milestones, include educational explanation cards such as:

* “The agent treated untrusted email content as instructions.”
* “This demonstrates indirect prompt injection.”
* “The model failed to separate data from commands.”

### **Pinned important events**

Important events should be pinnable or automatically pinned at the top of the panel.
Examples:

* first successful injection
* unsafe tool use
* win condition reached

### **Behavior**

* right column scrolls internally
* filters update timeline contents without reloading the whole page
* explanation cards should be visually distinct from ordinary event cards

---

## **7\. State Model**

### **7.1 Workspace states**

The center workspace should support these states:

1. **Default / idle**
   * tool strip visible
   * no tool pane open
   * transcript expanded
   * composer visible
2. **Tool-open**
   * tool strip visible
   * one tool pane open
   * transcript resized but visible
   * composer visible
3. **Active streaming**
   * transcript and/or event stream receiving live updates
   * unread indicators optional
4. **Success state**
   * win condition met
   * show status update and explanation card
   * do not interrupt the workspace with a blocking modal by default
5. **Failure / recoverable error state**
   * action failed or invalid
   * show actionable inline error message

---

## **8\. Notifications and Toasts**

Toasts may be used, but only for short-lived operational feedback.

### **Good toast use cases**

* Email sent
* Tool action completed
* Objective updated
* Success detected

### **Not appropriate for toast-only treatment**

* detailed educational explanation
* event history
* vulnerability interpretation

Rule:

* any important event shown in a toast must also be represented in the right-side event timeline if it matters for learning or traceability

---

## **9\. Copy and Microcopy Requirements**

The UI must help the user understand what to do without narration.

### **Required labels**

The following must be explicit in the interface:

* what the learner is trying to achieve
* which controls are attacker tools
* which box is the agent conversation
* which panel contains feedback / events

### **Examples of useful text**

* “Mission”
* “Success Criteria”
* “Recommended Steps”
* “Attack Tools”
* “Conversation with Agent”
* “Activity Timeline”
* “Why This Matters”

Forms should use clear field labels and supporting text where needed, consistent with current usability guidance for reducing cognitive load. ([nngroup.com](https://www.nngroup.com/articles/4-principles-reduce-cognitive-load/?utm_source=chatgpt.com))

---

## **10\. Responsive Behavior**

This spec is desktop-first.

### **Tablet / narrow desktop**

* left and right columns may become collapsible drawers
* center workspace remains primary
* tool pane behavior remains the same

### **Mobile**

Not required for the first implementation unless explicitly prioritized. If implemented later:

* center workspace becomes the main screen
* lab guide and feedback move into slide-over panels or bottom sheets
* maintain access to mission and feedback without losing the active task context, which is consistent with common contextual panel patterns. ([nngroup.com](https://www.nngroup.com/articles/bottom-sheet/?utm_source=chatgpt.com))

---

## **11\. Accessibility and Usability Requirements**

* All interactive controls must be keyboard accessible.
* Tool icons require accessible labels.
* Focus order must be logical.
* Color must not be the only differentiator for message type or event severity.
* Motion for pane expansion/collapse should be subtle and should respect reduced-motion settings.
* Scrollable regions should be visually obvious.

---

## **12\. MVP Acceptance Criteria**

The implementation is acceptable for v1 if all of the following are true:

1. The learner can see the mission and success criteria without scrolling the whole page.
2. The learner can use an attacker tool without losing access to the transcript.
3. The learner can see real-time events in a dedicated feedback area.
4. The learner can filter the event stream by type.
5. The interface does not require constant vertical page scrolling.
6. The user can understand what they are supposed to do without external narration.
7. Important learning-relevant events include short explanations, not just system logs.

---

## **13\. Suggested Implementation Notes**

These are implementation notes, not strict visual design requirements.

* Use a full-height app shell.
* Prefer CSS grid for the 3-column desktop layout.
* Use flex layout inside each column for vertical distribution.
* The transcript and right column should use internal overflow scrolling.
* Keep the composer pinned at the bottom of the center column.
* Animate tool-pane open/close with a short transition.
* Preserve form state and transcript scroll state across tool switches.

---

## **14\. Summary**

The target UI is not a vertical stack of independent widgets. It is a structured learning workspace with:

* persistent guidance on the left,
* active work in the center,
* reflection and progress on the right.

The central interaction pattern is:
**tool strip \-\> expandable tool pane \-\> persistent transcript \-\> fixed composer**

This pattern should be treated as the default desktop experience for the AI agent security lab.

---

## **15\. Frontend Implementation Spec**

This section translates the UI spec into an implementation-oriented structure for a coding agent.

## **15.1 Recommended Component Tree**

AppShell
├── TopBar
├── MainLayout
│   ├── LabGuideColumn
│   │   ├── LabHeaderCard
│   │   ├── MissionCard
│   │   ├── ScenarioCard
│   │   ├── SuccessCriteriaCard
│   │   ├── RecommendedStepsCard
│   │   ├── HintAccordion
│   │   └── LearningObjectiveCard
│   │
│   ├── WorkspaceColumn
│   │   ├── ToolStrip
│   │   ├── ToolPane
│   │   │   ├── EmailToolForm
│   │   │   ├── FilesToolPanel
│   │   │   ├── PayloadsToolPanel
│   │   │   ├── NotesToolPanel
│   │   │   └── ReconToolPanel
│   │   ├── TranscriptPanel
│   │   │   ├── TranscriptHeader
│   │   │   ├── TranscriptMessageList
│   │   │   └── ScrollToLatestButton
│   │   └── MessageComposer
│   │
│   └── FeedbackColumn
│       ├── StatusSummaryCard
│       ├── ObjectiveProgressCard
│       ├── EventFilterBar
│       ├── PinnedEventsSection
│       ├── EventTimeline
│       └── ExplanationCardStack
│
└── ToastViewport

### **Notes**

* `ToolPane` is a single container whose content changes based on the selected tool.
* `TranscriptPanel` and `EventTimeline` must be independently scrollable.
* `MessageComposer` stays pinned at the bottom of the center column.

---

## **15.2 Recommended State Shape**

Use a single page-level workspace state plus local component state where appropriate.

### **Example page state**

interface LabWorkspaceState {
  selectedTool: ToolKey | null;
  toolPaneOpen: boolean;
  toolPaneHeight: number;

  transcriptAutoScrollEnabled: boolean;
  transcriptUnreadCount: number;

  eventFilters: {
    types: EventType\[\];
    granularity: EventGranularity;
  };

  pinnedEventIds: string\[\];
  activeObjectiveIds: string\[\];
  completedObjectiveIds: string\[\];

  labStatus: 'idle' | 'active' | 'success' | 'error';
  agentStatus: 'idle' | 'processing' | 'acted';
  attackStatus: 'none' | 'partial' | 'success';
}

### **Tool state example**

interface EmailToolState {
  from: string;
  subject: string;
  body: string;
  isSending: boolean;
  error: string | null;
  dirty: boolean;
}

### **Core enums**

type ToolKey \= 'email' | 'files' | 'payloads' | 'notes' | 'recon';

type EventType \=
  | 'important'
  | 'attacker\_action'
  | 'agent\_action'
  | 'tool\_call'
  | 'system'
  | 'explanation';

type EventGranularity \= 'high' | 'detailed' | 'full';

---

## **15.3 Layout Tokens**

These tokens are meant to make implementation consistent and easy to adjust.

export const layout \= {
  topBarHeight: 56,
  columnGap: 16,
  pagePadding: 16,

  leftColumnMin: 280,
  leftColumnMax: 360,
  centerColumnMin: 520,
  rightColumnMin: 300,
  rightColumnMax: 420,

  toolStripHeight: 56,
  toolPaneMinHeight: 220,
  toolPaneMaxHeight: 320,
  composerMinHeight: 72,

  panelBorderRadius: 16,
  panelPadding: 16,
};

### **CSS grid suggestion**

.main-layout {
  display: grid;
  grid-template-columns: minmax(280px, 22%) minmax(520px, 1fr) minmax(300px, 26%);
  gap: 16px;
  height: calc(100vh \- 56px);
  padding: 16px;
  overflow: hidden;
}

### **Workspace column suggestion**

.workspace-column {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.tool-strip {
  flex: 0 0 56px;
}

.tool-pane {
  flex: 0 0 auto;
  overflow: auto;
}

.transcript-panel {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.message-composer {
  flex: 0 0 auto;
}

---

## **15.4 Interaction Rules**

### **Tool strip behavior**

1. Clicking a tool when no tool is open:
   * sets `selectedTool`
   * sets `toolPaneOpen = true`
   * expands the tool pane
2. Clicking the currently selected tool:
   * collapses the tool pane
   * keeps tool form state in memory
   * sets `toolPaneOpen = false`
3. Clicking a different tool while a tool is open:
   * switches `selectedTool`
   * preserves prior tool state
   * does not collapse the pane first

### **Transcript behavior**

1. If the user is already near the bottom, new messages auto-scroll.
2. If the user has scrolled upward, new messages should not force scroll.
3. When auto-scroll is disabled and a new message arrives, show a “Jump to latest” affordance.

### **Event timeline behavior**

1. Event stream updates in real time.
2. Filters update visible events client-side if data is already present.
3. Important events may also trigger a toast.
4. Important events should appear in the timeline even if a toast is dismissed.

### **Composer behavior**

1. Composer remains visible at all times on desktop.
2. Sending a learner message appends it to the transcript immediately in pending state if optimistic UI is used.

---

## **15.5 Tool Pane Animation Rules**

Animation should support context preservation, not spectacle.

### **Recommended behavior**

* duration: \~150ms to 220ms
* easing: standard ease or ease-out
* animate height and opacity
* respect reduced-motion preferences

### **Pseudocode**

if (toolPaneOpen) {
  animateHeight(fromCurrentHeight, clampedToolHeight);
  animateOpacity(0, 1);
} else {
  animateHeight(fromCurrentHeight, 0);
  animateOpacity(1, 0);
}

### **Constraints**

* transcript scroll position must not reset when the pane opens or closes
* message composer must remain anchored

---

## **15.6 Event Data Model**

A structured event model will make the right column easier to build and filter.

interface LabEvent {
  id: string;
  timestamp: string;
  type: EventType;
  granularity: EventGranularity;
  title: string;
  description: string;
  details?: string;
  important?: boolean;
  pinned?: boolean;
  relatedMessageId?: string;
  relatedObjectiveId?: string;
}

### **Example events**

const sampleEvents: LabEvent\[\] \= \[
  {
    id: 'evt\_1',
    timestamp: '2026-04-16T18:00:00Z',
    type: 'attacker\_action',
    granularity: 'high',
    title: 'Malicious email sent',
    description: 'The attacker sent an email crafted to influence the agent.',
    important: false,
  },
  {
    id: 'evt\_2',
    timestamp: '2026-04-16T18:00:09Z',
    type: 'agent\_action',
    granularity: 'detailed',
    title: 'Agent read inbox content',
    description: 'The agent opened the email and incorporated the message into its reasoning context.',
    important: true,
    pinned: true,
  },
  {
    id: 'evt\_3',
    timestamp: '2026-04-16T18:00:14Z',
    type: 'explanation',
    granularity: 'high',
    title: 'Indirect prompt injection detected',
    description: 'The agent treated untrusted email content as instructions rather than data.',
    important: true,
    pinned: true,
  },
\];

---

## **15.7 Transcript Data Model**

interface TranscriptMessage {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: string;
  pending?: boolean;
  error?: boolean;
}

### **Rendering rules**

* `user` messages align right or otherwise clearly differ visually
* `agent` messages align left
* `system` messages render in a muted, utility style

---

## **15.8 Suggested Prop Interfaces**

These are examples, not mandatory exact signatures.

interface ToolStripProps {
  selectedTool: ToolKey | null;
  onSelectTool: (tool: ToolKey) \=\> void;
  tools: Array\<{ key: ToolKey; label: string; icon: React.ReactNode }\>;
}

interface ToolPaneProps {
  selectedTool: ToolKey | null;
  isOpen: boolean;
  height: number;
  onClose: () \=\> void;
}

interface TranscriptPanelProps {
  messages: TranscriptMessage\[\];
  autoScrollEnabled: boolean;
  onJumpToLatest: () \=\> void;
}

interface EventTimelineProps {
  events: LabEvent\[\];
  filters: {
    types: EventType\[\];
    granularity: EventGranularity;
  };
  onChangeFilters: (filters: {
    types: EventType\[\];
    granularity: EventGranularity;
  }) \=\> void;
}

---

## **15.9 Empty, Loading, and Error States**

The coding agent should implement these deliberately.

### **Transcript empty state**

* show a short prompt such as: “Start interacting with the agent to begin the lab.”

### **Event timeline empty state**

* show: “Events will appear here as the lab progresses.”

### **Tool error state**

For example, if email send fails:

* show inline error in the tool pane
* preserve user input
* do not close the pane automatically

### **Streaming/loading state**

* show lightweight loading indicators for agent processing and tool actions
* avoid full-screen spinners

---

## **15.10 Toast Rules for Implementation**

interface ToastEvent {
  id: string;
  title: string;
  description?: string;
  severity: 'info' | 'success' | 'warning' | 'error';
}

### **Emit toast for**

* email sent
* objective updated
* success reached
* action failed

### **Do not rely on toast for**

* explanation of why an exploit worked
* full event trace

---

## **15.11 Accessibility Checklist for Implementation**

* every tool button has an accessible label
* tool strip reachable via keyboard tab order
* pane open/close state exposed to assistive tech
* event filters keyboard accessible
* composer supports keyboard send shortcut if desired
* reduced-motion mode disables or simplifies pane animation
* contrast is sufficient for message types and state badges

---

## **15.12 Suggested Engineering Sequence**

A practical build order:

1. Build the 3-column app shell.
2. Implement the left-column guide with static content.
3. Implement the center column with transcript \+ composer.
4. Add the tool strip and expandable pane.
5. Build the email tool form first.
6. Build the right-column event timeline with mock data.
7. Add filtering.
8. Add live updates / streaming integration.
9. Add toasts and pinned events.
10. Polish animation, empty states, and accessibility.

---

## **15.13 Implementation Acceptance Criteria**

The frontend implementation is complete enough for handoff/testing when:

* the 3-column layout renders correctly at desktop width
* the center tool pane expands/collapses without hiding the transcript
* transcript and events scroll independently
* message composer stays anchored at the bottom of the center column
* tool switching preserves input state
* the event timeline supports filtering by type
* important events can be pinned or surfaced distinctly
* the lab can be understood from the visible UI alone
