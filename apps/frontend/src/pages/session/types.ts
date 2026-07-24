import type { components } from "../../api/generated";

export type GetSessionMetadataResponse =
  components["schemas"]["GetSessionMetadataResponse"];
export type GetSessionReportDraftResponse =
  components["schemas"]["GetSessionReportDraftResponse"];
export type GetSessionReportEvidenceResponse =
  components["schemas"]["GetSessionReportEvidenceResponse"];
export type GetSessionTraceResponse =
  components["schemas"]["GetSessionTraceResponse"];
export type ImportSelectedEvidenceRequest =
  components["schemas"]["ImportSelectedEvidenceRequest"];
export type ImportSelectedEvidenceResponse =
  components["schemas"]["ImportSelectedEvidenceResponse"];
export type PutSessionReportDraftRequest =
  components["schemas"]["PutSessionReportDraftRequest"];
export type PutSessionReportEvidenceRequest =
  components["schemas"]["PutSessionReportEvidenceRequest"];
export type ReportEvidenceItem = components["schemas"]["ReportEvidenceItem"];
export type SessionCompletionStatus =
  components["schemas"]["SessionMetadataResponse"]["completion_status"];
export type SessionTraceEvent = components["schemas"]["SessionTraceEvent"];
export type SessionProgressChip =
  components["schemas"]["SessionProgressChipResponse"];
export type SessionHint = components["schemas"]["SessionHintResponse"];
export type SessionFeedbackItem =
  components["schemas"]["SessionFeedbackResponse"];
export type SessionRuntimeFile =
  components["schemas"]["SessionRuntimeFileResponse"];
export type SessionMetadata = components["schemas"]["SessionMetadataResponse"];
export type MarkSessionHintsSeenResponse =
  components["schemas"]["MarkSessionHintsSeenResponse"];

export type TranscriptRole = "user" | "agent" | "policy" | "system";

export type TranscriptEntry = {
  role: TranscriptRole;
  content: string;
  timestamp: string;
};

export type LearnerFeedbackItem = {
  status: components["schemas"]["GetFeedbackResponse"]["feedback"][number]["status"];
  reason_code: string;
  evidence_snippet: string;
};
export type LearnerFeedbackStatus = LearnerFeedbackItem["status"];

export type InjectSessionEmailResponse =
  components["schemas"]["InjectSessionEmailResponse"];

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
  simulated: boolean;
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
