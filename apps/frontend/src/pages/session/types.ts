import type {
  GetFeedbackResponse,
  GetSessionMetadataResponse,
  GetSessionReportEvidenceResponse,
  GetSessionTraceResponse,
  ImportSelectedEvidenceRequest,
  ImportSelectedEvidenceResponse,
  PutSessionReportEvidenceRequest,
  ReportEvidenceItem,
  SessionCompletionStatus,
  SessionFeedbackResponse,
  SessionHintResponse,
  SessionMetadataResponse,
  SessionProgressChipResponse,
  SessionRuntimeFileResponse,
  SessionTraceEvent,
} from "../../../../contracts/ts/index";

export type {
  GetSessionMetadataResponse,
  GetSessionReportEvidenceResponse,
  GetSessionTraceResponse,
  ImportSelectedEvidenceRequest,
  ImportSelectedEvidenceResponse,
  PutSessionReportEvidenceRequest,
  ReportEvidenceItem,
  SessionCompletionStatus,
  SessionTraceEvent,
};
export type SessionProgressChip = SessionProgressChipResponse;
export type SessionHint = SessionHintResponse;
export type SessionFeedbackItem = SessionFeedbackResponse;
export type SessionRuntimeFile = SessionRuntimeFileResponse;
export type SessionMetadata = SessionMetadataResponse;

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
export type EvidenceType =
  | "exploit_step"
  | "exploit_outcome"
  | "system_context"
  | "coaching_feedback"
  | "noise";
export type EvidencePriority = "high" | "medium" | "low";

export type TimelineEvent = {
  id: string;
  timestamp: string;
  type: EventType;
  granularity: EventGranularity;
  title: string;
  description: string;
  details?: string;
  important?: boolean;
  report_selectable?: boolean;
  evidence_type?: EvidenceType;
  objective_keys?: string[];
  why_it_matters?: string | null;
  default_priority?: EvidencePriority;
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
