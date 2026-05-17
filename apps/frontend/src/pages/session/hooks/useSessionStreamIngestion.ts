import type { Dispatch, MutableRefObject, SetStateAction } from "react";
import { useEffect, useRef } from "react";
import type { ServerMessage } from "../../../hooks/useSessionStream";
import type {
  AgentStatus,
  LearnerFeedbackItem,
  SessionMetadata,
  TranscriptEntry,
} from "../types";

type UseSessionStreamIngestionParams = {
  messages: ServerMessage[];
  ensureRevealLoop: () => void;
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
  refreshSessionMetadata: () => Promise<void>;
};

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
          void params.refreshSessionMetadata();
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
        if (message.payload.event_code === "MODEL_TURN_COMPLETED") {
          void params.refreshSessionMetadata();
        }
        params.setTranscriptEntries((entries) => [
          ...entries,
          {
            role: "system",
            content: `[${message.payload.event_code}] ${message.payload.message}`,
            timestamp: message.timestamp,
          },
        ]);
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
    params.registerLearnerFeedbackEvents,
    params.activeEntryTsRef,
    params.finalizePendingRef,
    params.pendingBufferRef,
    params.setIsAwaitingResponse,
    params.setTranscriptEntries,
    params.setMetadata,
    params.setAgentStatus,
    params.refreshSessionMetadata,
  ]);
}
