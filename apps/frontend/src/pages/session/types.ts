import type {
  GetFeedbackResponse,
  GetSessionTraceResponse,
  SessionTraceEvent,
} from "../../../../contracts/ts/index";

export type SessionCompletionStatus =
  | "in_progress"
  | "completed_success"
  | "completed_failure";

export type SessionProgressChip = {
  objective_key: string;
  label: string;
  status: "pending" | "complete";
  completed_at: string | null;
  updated_at: string;
};

export type SessionHint = {
  hint_key: string;
  text: string;
  sort_order: number;
  status: "pending" | "unlocked";
  unlock_at: string;
  unlocked_at: string | null;
  seen_at: string | null;
};

export type SessionFeedbackSeverity = "info" | "warning" | "error";

export type SessionFeedbackItem = {
  id: string;
  feedback_key: string;
  reason_code: string;
  message: string;
  severity: SessionFeedbackSeverity;
  trigger_event_index: number | null;
  created_at: string;
  seen_at: string | null;
};

export type SessionRuntimeFile = {
  path: string;
  content: string;
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
  completion_status: SessionCompletionStatus;
  completed_at: string | null;
  completion_reason_code: string | null;
  progress_chips: SessionProgressChip[];
  hints: SessionHint[];
  unread_hint_count: number;
  feedback_items: SessionFeedbackItem[];
  feedback: SessionFeedbackItem[];
  unread_feedback_count: number;
  runtime_files?: SessionRuntimeFile[];
};

export type GetSessionMetadataResponse = {
  session: SessionMetadata;
};

export type { GetSessionTraceResponse, SessionTraceEvent };

export type MarkSessionHintsSeenResponse = {
  session_id: string;
  updated_count: number;
};

export type TranscriptRole = "user" | "agent" | "policy" | "system";

export type TranscriptEntry = {
  role: TranscriptRole;
  content: string;
  timestamp: string;
};

export type LearnerFeedbackItem = {
  status: GetFeedbackResponse["feedback"][number]["status"];
  reason_code: string;
  evidence_snippet: string;
};
export type LearnerFeedbackStatus = LearnerFeedbackItem["status"];

export type InjectSessionEmailResponse = {
  session_id: string;
  email_id: string | null;
  accepted: boolean;
};

export type ToolKey =
  | "email"
  | "files"
  | "payloads"
  | "notes"
  | "recon"
  | "logs"
  | "invoices";

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

export type SessionTelemetryLog = {
  id: string;
  message: string;
  created_at: string;
  log_case: string;
};

export type SessionInvoice = {
  id: string;
  invoice_id: string;
  vendor_name: string;
  amount: number;
  currency: string;
  created_at: string;
  handled_by: string | null;
  handled_at: string | null;
};

export type SessionWorkspaceState = {
  selectedTool: ToolKey | null;
  toolPaneOpen: boolean;
};
