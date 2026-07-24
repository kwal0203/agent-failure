export type EvaluatorFeedbackStatusType =
  | "learned"
  | "progress"
  | "no_progress"
  | "session_terminal";

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
