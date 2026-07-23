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
  const {
    messages,
    ensureRevealLoop,
    registerLearnerFeedbackEvents,
    activeEntryTsRef,
    pendingBufferRef,
    finalizePendingRef,
    setIsAwaitingResponse,
    setTranscriptEntries,
    setMetadata,
    setAgentStatus,
    refreshSessionMetadata,
  } = params;
  const processedMessageCount = useRef(0);

  useEffect(() => {
    if (processedMessageCount.current > messages.length) {
      processedMessageCount.current = 0;
    }

    const newMessages = messages.slice(processedMessageCount.current);
    if (newMessages.length === 0) return;

    for (const message of newMessages) {
      if (message.type === "SESSION_STATUS") {
        setMetadata((prev) =>
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
          setAgentStatus("idle");
        }
        continue;
      }

      if (message.type === "AGENT_TEXT_CHUNK") {
        setAgentStatus("active");
        if (!activeEntryTsRef.current) {
          activeEntryTsRef.current = message.timestamp;
        }
        pendingBufferRef.current += message.payload.content;
        if (message.payload.final) {
          setAgentStatus("idle");
          finalizePendingRef.current = true;
          void refreshSessionMetadata();
        }
        ensureRevealLoop();
        continue;
      }

      if (message.type === "POLICY_DENIAL") {
        setTranscriptEntries((entries) => [
          ...entries,
          {
            role: "policy",
            content: message.payload.message,
            timestamp: message.timestamp,
          },
        ]);
        setIsAwaitingResponse(false);
        setAgentStatus("idle");
        continue;
      }

      if (message.type === "TRACE_EVENT") {
        if (
          message.payload.event_code === "TURN_STARTED" ||
          message.payload.event_code === "MODEL_REQUEST_STARTED"
        ) {
          setAgentStatus("active");
          continue;
        }
        if (message.payload.event_code === "MODEL_TURN_COMPLETED") {
          void refreshSessionMetadata();
        }
        setTranscriptEntries((entries) => [
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
        setTranscriptEntries((entries) => [
          ...entries,
          {
            role: "system",
            content: message.payload.message,
            timestamp: message.timestamp,
          },
        ]);
        setIsAwaitingResponse(false);
        setAgentStatus("idle");
        continue;
      }

      if (message.type === "LEARNER_FEEDBACK") {
        registerLearnerFeedbackEvents(
          message.payload.feedback,
          message.timestamp,
        );
      }
    }

    processedMessageCount.current = messages.length;
  }, [
    messages,
    ensureRevealLoop,
    registerLearnerFeedbackEvents,
    activeEntryTsRef,
    finalizePendingRef,
    pendingBufferRef,
    setIsAwaitingResponse,
    setTranscriptEntries,
    setMetadata,
    setAgentStatus,
    refreshSessionMetadata,
  ]);
}
