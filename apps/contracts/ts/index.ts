export type TraceFamily = "lifecycle" | "learner" | "runtime" | "tool" | "model";

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
};

export type GetSessionTraceResponse = {
  events: SessionTraceEvent[];
  next_cursor?: string | null;
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
