export type TraceFamily = "lifecycle" | "learner" | "runtime" | "tool" | "model";
export type SessionCompletionStatus =
  | "in_progress"
  | "completed_success"
  | "completed_failure";

export type EvaluatorFeedbackStatusType =
  | "learned"
  | "progress"
  | "no_progress"
  | "session_terminal";

export type LabCapabilitiesResponse = {
  supports_resume: boolean;
  supports_uploads: boolean;
};

export type LabCatalogItemResponse = {
  id: string;
  slug: string;
  name: string;
  summary: string;
  capabilities: LabCapabilitiesResponse;
};

export type GetLabsResponse = {
  labs: LabCatalogItemResponse[];
};

export type EvaluatorFeedbackResponse = {
  status: EvaluatorFeedbackStatusType;
  reason_code: string;
  evidence_snippet: string;
};

export type GetFeedbackResponse = {
  feedback: EvaluatorFeedbackResponse[];
};

export type SessionTraceEvent = {
  id: string;
  event_index: number;
  family: TraceFamily;
  event_type: string;
  source: string;
  occurred_at: string;
  payload: Record<string, unknown>;
  report_selectable: boolean;
  evidence_type:
    | "exploit_step"
    | "exploit_outcome"
    | "system_context"
    | "coaching_feedback"
    | "noise";
  objective_keys: string[];
  why_it_matters: string | null;
  default_priority: "high" | "medium" | "low";
};

export type GetSessionTraceResponse = {
  events: SessionTraceEvent[];
  next_cursor?: string | null;
};

export type ReportEvidenceItem = {
  event_id: string;
  position: number;
  title: string;
  description: string | null;
  details: Record<string, unknown> | null;
  occurred_at: string;
  trace_version: number;
  event_index: number;
  evidence_type:
    | "exploit_step"
    | "exploit_outcome"
    | "system_context"
    | "coaching_feedback"
    | "noise";
  objective_keys: string[];
  why_it_matters: string | null;
  default_priority: "high" | "medium" | "low";
  citation_label: string | null;
  objective_mapping: ObjectiveMappingItem[] | null;
  evidence_strength: "high" | "medium" | "low" | null;
  student_note: string | null;
};

export type ObjectiveMappingItem = {
  objective_key: string;
  label: string;
  rubric_target: string;
};

export type GetSessionReportEvidenceResponse = {
  items: ReportEvidenceItem[];
};

export type PutSessionReportEvidenceRequest = {
  items: ReportEvidenceItem[];
};

export type ImportSelectedEvidenceRequest = {
  event_ids?: string[] | null;
};

export type ImportSelectedEvidenceResponse = {
  items: ReportEvidenceItem[];
};

export type SessionProgressChipResponse = {
  objective_key: string;
  label: string;
  status: "pending" | "complete";
  completed_at: string | null;
  updated_at: string;
};

export type SessionHintResponse = {
  hint_key: string;
  text: string;
  sort_order: number;
  status: "pending" | "unlocked";
  unlock_at: string;
  unlocked_at: string | null;
  seen_at: string | null;
};

export type SessionFeedbackResponse = {
  id: string;
  feedback_key: string;
  reason_code: string;
  message: string;
  severity: "info" | "warning" | "error";
  trigger_event_index: number | null;
  created_at: string;
  seen_at: string | null;
};

export type SessionRuntimeFileResponse = {
  path: string;
  content: string;
  updated_at: string;
};

export type SessionMetadataResponse = {
  id: string;
  lab_id: string | null;
  lab_version_id: string | null;
  lab_difficulty: string;
  state: string;
  runtime_substate: string | null;
  resume_mode: string;
  last_transition_reason: string | null;
  interactive: boolean;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  completion_status: SessionCompletionStatus;
  completed_at: string | null;
  completion_reason_code: string | null;
  provisioning_stalled: boolean;
  provisioning_stall_reason_code: string | null;
  progress_chips: SessionProgressChipResponse[];
  hints: SessionHintResponse[];
  unread_hint_count: number;
  feedback_items: SessionFeedbackResponse[];
  feedback: SessionFeedbackResponse[];
  unread_feedback_count: number;
  runtime_files: SessionRuntimeFileResponse[];
};

export type GetSessionMetadataResponse = {
  session: SessionMetadataResponse;
};

export type LearnerFeedbackItem = {
  status: EvaluatorFeedbackStatusType;
  reason_code: string;
  evidence_snippet: string;
};

export type SessionStatusMessage = {
  type: "SESSION_STATUS";
  session_id: string;
  timestamp: string;
  payload: {
    state: string;
    runtime_substate: string | null;
    interactive: boolean;
  };
};

export type AgentTextChunkMessage = {
  type: "AGENT_TEXT_CHUNK";
  session_id: string;
  timestamp: string;
  payload: {
    content: string;
    final: boolean;
  };
};

export type PolicyDenialMessage = {
  type: "POLICY_DENIAL";
  session_id: string;
  timestamp: string;
  payload: {
    reason_code: string;
    message: string;
  };
};

export type TraceEventMessage = {
  type: "TRACE_EVENT";
  session_id: string;
  timestamp: string;
  payload: {
    event_code: string;
    message: string;
  };
};

export type SystemErrorMessage = {
  type: "SYSTEM_ERROR";
  session_id: string;
  timestamp: string;
  payload: {
    error_code: string;
    message: string;
  };
};

export type LearnerFeedbackMessage = {
  type: "LEARNER_FEEDBACK";
  session_id: string;
  timestamp: string;
  payload: {
    feedback: LearnerFeedbackItem[];
  };
};

export type ServerMessage =
  | SessionStatusMessage
  | AgentTextChunkMessage
  | TraceEventMessage
  | PolicyDenialMessage
  | SystemErrorMessage
  | LearnerFeedbackMessage;
