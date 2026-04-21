import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { useEffect, useRef } from "react";
import type { ServerMessage } from "../../../hooks/useSessionStream";
import type {
  AgentStatus,
  LearnerFeedbackItem,
  SessionMetadata,
  TimelineEvent,
  TranscriptEntry,
} from "../types";

type UseSessionStreamIngestionParams = {
  messages: ServerMessage[];
  ensureRevealLoop: () => void;
  appendTimelineEvent: (event: TimelineEvent) => void;
  registerLearnerFeedbackEvents: (
    feedback: LearnerFeedbackItem[],
    timestamp: string,
  ) => void;
  activeEntryTsRef: MutableRefObject<string | null>;
  pendingBufferRef: MutableRefObject<string>;
  finalizePendingRef: MutableRefObject<boolean>;
  setIsAwaitingResponse: Dispatch<SetStateAction<boolean>>;
  setTranscriptEntries: Dispatch<SetStateAction<TranscriptEntry[]>>;
  setMetadata: Dispatch<SetStateAction<SessionMetadata | null>>;
  setAgentStatus: (status: AgentStatus) => void;
};

function formatTraceTitle(eventCode: string, message: string): string {
  const normalizedMessage = message.toLowerCase();

  if (
    eventCode === "TOOL_CALL_SUCCEEDED" &&
    normalizedMessage.includes("write_memory")
  ) {
    return "Memory write accepted";
  }

  if (
    eventCode === "TOOL_CALL_SUCCEEDED" &&
    normalizedMessage.includes("retrieve_memory")
  ) {
    return "Payment memory retrieved";
  }

  if (
    eventCode === "TOOL_CALL_SUCCEEDED" &&
    normalizedMessage.includes("pay_invoice")
  ) {
    return "Invoice payment routed";
  }

  if (
    eventCode === "TOOL_CALL_REQUESTED" &&
    normalizedMessage.includes("pay_invoice")
  ) {
    return "Invoice payment requested";
  }

  if (
    eventCode === "TOOL_CALL_FAILED" &&
    normalizedMessage.includes("pay_invoice")
  ) {
    return "Invoice payment failed";
  }

  return eventCode;
}

export function useSessionStreamIngestion(
  params: UseSessionStreamIngestionParams,
) {
  const processedMessageCount = useRef(0);

  useEffect(() => {
    if (processedMessageCount.current > params.messages.length) {
      processedMessageCount.current = 0;
    }

    const newMessages = params.messages.slice(processedMessageCount.current);
    if (newMessages.length === 0) return;

    for (const message of newMessages) {
      if (message.type === "SESSION_STATUS") {
        params.setMetadata((prev) =>
          prev
            ? {
                ...prev,
                state: message.payload.state,
                runtime_substate: message.payload.runtime_substate,
                interactive: message.payload.interactive,
              }
            : prev,
        );
        params.appendTimelineEvent({
          id: `status-${message.timestamp}-${message.payload.state}-${message.payload.runtime_substate ?? "none"}`,
          timestamp: message.timestamp,
          type: "system",
          granularity: "high",
          title: "Session status updated",
          description: `${message.payload.state}${message.payload.runtime_substate ? ` · ${message.payload.runtime_substate}` : ""}`,
        });
        if (message.payload.state !== "ACTIVE") {
          params.setAgentStatus("idle");
        }
        continue;
      }

      if (message.type === "AGENT_TEXT_CHUNK") {
        params.setAgentStatus("active");
        if (!params.activeEntryTsRef.current) {
          params.activeEntryTsRef.current = message.timestamp;
        }
        params.pendingBufferRef.current += message.payload.content;
        if (message.payload.final) {
          params.setAgentStatus("idle");
          params.finalizePendingRef.current = true;
          params.appendTimelineEvent({
            id: `agent-final-${message.timestamp}`,
            timestamp: message.timestamp,
            type: "agent_action",
            granularity: "detailed",
            title: "Agent response completed",
            description: "A streamed response finished in the transcript.",
          });
        }
        params.ensureRevealLoop();
        continue;
      }

      if (message.type === "POLICY_DENIAL") {
        params.setTranscriptEntries((entries) => [
          ...entries,
          {
            role: "policy",
            content: message.payload.message,
            timestamp: message.timestamp,
          },
        ]);
        params.setIsAwaitingResponse(false);
        params.setAgentStatus("idle");
        params.appendTimelineEvent({
          id: `policy-denial-${message.timestamp}-${message.payload.code}`,
          timestamp: message.timestamp,
          type: "important",
          granularity: "high",
          title: "Policy denial",
          description: message.payload.message,
          details: `Policy code: ${message.payload.code}`,
          important: true,
        });
        continue;
      }

      if (message.type === "TRACE_EVENT") {
        if (
          message.payload.event_code === "TURN_STARTED" ||
          message.payload.event_code === "MODEL_REQUEST_STARTED"
        ) {
          params.setAgentStatus("active");
          continue;
        }
        params.setTranscriptEntries((entries) => [
          ...entries,
          {
            role: "system",
            content: `[${message.payload.event_code}] ${message.payload.message}`,
            timestamp: message.timestamp,
          },
        ]);
        params.appendTimelineEvent({
          id: `trace-${message.timestamp}-${message.payload.event_code}`,
          timestamp: message.timestamp,
          type: message.payload.event_code.includes("TOOL")
            ? "tool_call"
            : "system",
          granularity: "detailed",
          title: formatTraceTitle(
            message.payload.event_code,
            message.payload.message,
          ),
          description: message.payload.message,
        });
        continue;
      }

      if (message.type === "SYSTEM_ERROR") {
        params.setTranscriptEntries((entries) => [
          ...entries,
          {
            role: "system",
            content: message.payload.message,
            timestamp: message.timestamp,
          },
        ]);
        params.setIsAwaitingResponse(false);
        params.setAgentStatus("idle");
        params.appendTimelineEvent({
          id: `system-error-${message.timestamp}-${message.payload.code}`,
          timestamp: message.timestamp,
          type: "important",
          granularity: "high",
          title: "System error",
          description: message.payload.message,
          details: `Error code: ${message.payload.code}`,
          important: true,
        });
        continue;
      }

      if (message.type === "LEARNER_FEEDBACK") {
        params.registerLearnerFeedbackEvents(
          message.payload.feedback,
          message.timestamp,
        );
      }
    }

    processedMessageCount.current = params.messages.length;
  }, [
    params.messages,
    params.ensureRevealLoop,
    params.appendTimelineEvent,
    params.registerLearnerFeedbackEvents,
    params.activeEntryTsRef,
    params.finalizePendingRef,
    params.pendingBufferRef,
    params.setIsAwaitingResponse,
    params.setTranscriptEntries,
    params.setMetadata,
    params.setAgentStatus,
  ]);
}
