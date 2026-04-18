export type SessionProgressChip = {
  objective_key: string;
  label: string;
  status: "pending" | "complete";
  completed_at: string | null;
  updated_at: string;
};

export type SessionMetadata = {
  id: string;
  lab_id: string | null;
  lab_version_id: string | null;
  state: string;
  runtime_substate: string | null;
  resume_mode: string;
  interactive: boolean;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  progress_chips: SessionProgressChip[];
};

export type GetSessionMetadataResponse = {
  session: SessionMetadata;
};

export type TranscriptRole = "user" | "agent" | "policy" | "system";

export type TranscriptEntry = {
  role: TranscriptRole;
  content: string;
  timestamp: string;
};

export type LearnerFeedbackStatus =
  | "learned"
  | "progress"
  | "no_progress"
  | "session_terminal";

export type LearnerFeedbackItem = {
  status: LearnerFeedbackStatus;
  reason_code: string;
  evidence_snippet: string;
};

export type GetFeedbackResponse = {
  feedback: LearnerFeedbackItem[];
};

export type InjectSessionEmailResponse = {
  session_id: string;
  email_id: string | null;
  accepted: boolean;
};

export type ToolKey = "email" | "files" | "payloads" | "notes" | "recon";

export type AgentStatus = "idle" | "active";

export type UnlockedHint = {
  index: number;
  text: string;
  unlockedAt: string;
};

export type EventType =
  | "important"
  | "attacker_action"
  | "agent_action"
  | "tool_call"
  | "system"
  | "explanation";

export type EventGranularity = "high" | "detailed" | "full";

export type TimelineEvent = {
  id: string;
  timestamp: string;
  type: EventType;
  granularity: EventGranularity;
  title: string;
  description: string;
  details?: string;
  important?: boolean;
};

export type SessionWorkspaceState = {
  selectedTool: ToolKey | null;
  toolPaneOpen: boolean;
  transcriptAutoScrollEnabled: boolean;
};
