import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  SESSION_METADATA_POLL_BASE_MS,
  SESSION_METADATA_POLL_JITTER_RATIO,
} from "../constants";
import { jitterDelayMs } from "../helpers";
import type {
  GetSessionMetadataResponse,
  GetSessionTraceResponse,
  LearnerFeedbackItem,
  SessionFeedbackItem,
  SessionMetadata,
  SessionProgressChip,
  SessionTraceEvent,
  TimelineEvent,
} from "../types";
import { API_BASE, AUTH_HEADER, humanizeFeedbackKey } from "../ui";

type UseSessionDataParams = {
  sessionId?: string;
};

type UseSessionDataResult = {
  metadata: SessionMetadata | null;
  setMetadata: Dispatch<SetStateAction<SessionMetadata | null>>;
  progressReady: boolean;
  timelineEvents: TimelineEvent[];
  feedbackError: string | null;
  feedbackLoading: boolean;
  feedbackReady: boolean;
  appendTimelineEvent: (event: TimelineEvent) => void;
  registerLearnerFeedbackEvents: (
    feedback: LearnerFeedbackItem[],
    timestamp: string,
  ) => void;
  refreshSessionMetadata: () => Promise<void>;
  sessionState: string;
  progressChips: SessionProgressChip[];
};

function formatPersistedTraceTitle(event: SessionTraceEvent): string {
  const toolName = event.payload.tool_name;
  const normalizedToolName =
    typeof toolName === "string" ? toolName.trim() : "";
  const humanizedToolName = normalizedToolName
    ? normalizedToolName
        .split("_")
        .filter((part) => part.length > 0)
        .map((part, idx) =>
          idx === 0
            ? part.charAt(0).toUpperCase() + part.slice(1)
            : part.toLowerCase(),
        )
        .join(" ")
    : "";
  if (
    event.event_type === "TOOL_CALL_SUCCEEDED" &&
    toolName === "write_memory"
  ) {
    return "Memory write accepted";
  }
  if (
    event.event_type === "TOOL_CALL_SUCCEEDED" &&
    toolName === "retrieve_memory"
  ) {
    return "Payment memory retrieved";
  }
  if (
    event.event_type === "TOOL_CALL_SUCCEEDED" &&
    toolName === "pay_invoice"
  ) {
    return "Invoice payment routed";
  }
  if (
    event.event_type === "TOOL_CALL_REQUESTED" &&
    toolName === "pay_invoice"
  ) {
    return "Invoice payment requested";
  }
  if (event.event_type === "TOOL_CALL_FAILED" && toolName === "pay_invoice") {
    return "Invoice payment failed";
  }
  if (event.event_type === "TOOL_CALL_REQUESTED" && humanizedToolName) {
    return `${humanizedToolName} requested`;
  }
  if (event.event_type === "TOOL_CALL_SUCCEEDED" && humanizedToolName) {
    return `${humanizedToolName} succeeded`;
  }
  if (event.event_type === "TOOL_CALL_FAILED" && humanizedToolName) {
    return `${humanizedToolName} failed`;
  }
  return event.event_type
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function mapPersistedTraceToTimelineEvent(
  event: SessionTraceEvent,
): TimelineEvent | null {
  const timestamp = event.occurred_at;
  const eventId = `trace-${event.id}`;
  if (event.event_type === "SESSION_CREATED") {
    return {
      id: eventId,
      timestamp,
      type: "system",
      granularity: "high",
      title: "Session created",
      description: "Lab session was created.",
    };
  }

  if (event.event_type === "MODEL_TURN_COMPLETED") {
    return {
      id: eventId,
      timestamp,
      type: "agent_action",
      granularity: "high",
      title: "Agent response completed",
      description: "Assistant completed a response turn.",
    };
  }

  if (event.event_type === "MODEL_TURN_FAILED") {
    const errorCode =
      typeof event.payload.error_code === "string"
        ? event.payload.error_code
        : "UNKNOWN";
    return {
      id: eventId,
      timestamp,
      type: "system",
      granularity: "high",
      title: "Agent response failed",
      description: `Model turn failed (${errorCode}).`,
      important: true,
    };
  }

  if (event.event_type === "ATTACK_EMAIL_SENT") {
    const subject =
      typeof event.payload.subject === "string" ? event.payload.subject : "";
    const emailFrom =
      typeof event.payload.email_from === "string"
        ? event.payload.email_from
        : "";
    const emailId =
      typeof event.payload.email_id === "string" && event.payload.email_id
        ? ` (id: ${event.payload.email_id})`
        : "";
    return {
      id: eventId,
      timestamp,
      type: "attacker_action",
      granularity: "high",
      title: "Email injected to inbox",
      description: `Email accepted${emailId}.`,
      details: `From: ${emailFrom}\nSubject: ${subject}`,
    };
  }

  if (event.event_type === "RUNTIME_PROVISION_REQUESTED") {
    return {
      id: eventId,
      timestamp,
      type: "system",
      granularity: "high",
      title: "Runtime provisioning requested",
      description: "Control plane requested runtime provisioning.",
    };
  }

  if (event.event_type === "RUNTIME_PROVISION_ACCEPTED") {
    return {
      id: eventId,
      timestamp,
      type: "system",
      granularity: "high",
      title: "Runtime provisioning accepted",
      description: "Runtime was provisioned and accepted.",
    };
  }

  if (event.event_type === "RUNTIME_PROVISION_FAILED") {
    const reasonCode =
      typeof event.payload.reason_code === "string"
        ? event.payload.reason_code
        : "UNKNOWN";
    return {
      id: eventId,
      timestamp,
      type: "system",
      granularity: "high",
      title: "Runtime provisioning failed",
      description: `Runtime provisioning failed (${reasonCode}).`,
      important: true,
    };
  }

  if (
    event.event_type === "TOOL_CALL_REQUESTED" ||
    event.event_type === "TOOL_CALL_SUCCEEDED" ||
    event.event_type === "TOOL_CALL_FAILED"
  ) {
    const toolName =
      typeof event.payload.tool_name === "string"
        ? event.payload.tool_name
        : "";
    const statusWord = event.event_type
      .replace("TOOL_CALL_", "")
      .toLowerCase()
      .replaceAll("_", " ");
    return {
      id: eventId,
      timestamp,
      type: "tool_call",
      granularity: "detailed",
      title: formatPersistedTraceTitle(event),
      description: toolName
        ? `${toolName} ${statusWord}`
        : event.event_type.toLowerCase().replaceAll("_", " "),
    };
  }

  if (event.event_type === "MALICIOUS_EMAIL_READ") {
    return {
      id: eventId,
      timestamp,
      type: "important",
      granularity: "high",
      title: "Malicious email entered model context",
      description: "Assistant read learner-injected malicious email content.",
      important: true,
    };
  }

  if (event.event_type === "TOKEN_DISCLOSURE_ATTEMPTED") {
    return {
      id: eventId,
      timestamp,
      type: "important",
      granularity: "high",
      title: "Token disclosure attempted",
      description: "Assistant attempted to disclose sensitive token material.",
      important: true,
    };
  }

  if (event.event_type === "TOKEN_DISCLOSED") {
    return {
      id: eventId,
      timestamp,
      type: "important",
      granularity: "high",
      title: "Token disclosed",
      description: "Sensitive token was exposed during the session.",
      important: true,
    };
  }

  return null;
}

export function useSessionData({
  sessionId,
}: UseSessionDataParams): UseSessionDataResult {
  const [metadata, setMetadata] = useState<SessionMetadata | null>(null);
  const [metadataReady, setMetadataReady] = useState(false);
  const seenFeedbackKeysRef = useRef(new Set<string>());
  const seenTimelineEventIdsRef = useRef(new Set<string>());
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);

  const appendTimelineEvent = useCallback((event: TimelineEvent) => {
    if (seenTimelineEventIdsRef.current.has(event.id)) {
      return;
    }
    seenTimelineEventIdsRef.current.add(event.id);
    setTimelineEvents((prev) => [...prev, event]);
  }, []);

  const refreshTraceTimeline = useCallback(async () => {
    if (!sessionId) return;

    try {
      const res = await fetch(
        `${API_BASE}/api/v1/sessions/${sessionId}/trace`,
        {
          method: "GET",
          headers: {
            Authorization: AUTH_HEADER,
            "Content-Type": "application/json",
          },
        },
      );
      if (!res.ok) {
        return;
      }

      const data = (await res.json()) as GetSessionTraceResponse;
      const events = Array.isArray(data.events) ? data.events : [];
      for (const event of events) {
        const timelineEvent = mapPersistedTraceToTimelineEvent(event);
        if (timelineEvent) {
          appendTimelineEvent(timelineEvent);
        }
      }
    } catch {
      return;
    }
  }, [appendTimelineEvent, sessionId]);

  const registerLearnerFeedbackEvents = useCallback(
    (_feedback: LearnerFeedbackItem[], _timestamp: string) => {
      // Metadata polling is the source of truth for feedback.
    },
    [],
  );

  const registerMetadataFeedbackEvents = useCallback(
    (feedbackItems: SessionFeedbackItem[]) => {
      for (const item of feedbackItems) {
        const key = item.id;
        if (seenFeedbackKeysRef.current.has(key)) continue;
        seenFeedbackKeysRef.current.add(key);
        appendTimelineEvent({
          id: `feedback-item-${key}`,
          timestamp: item.created_at,
          type: "explanation",
          granularity: "high",
          title: humanizeFeedbackKey(item.feedback_key),
          description: item.message,
          details: `${item.severity} · ${item.reason_code}`,
          important: item.severity === "error",
        });
      }
    },
    [appendTimelineEvent],
  );

  const refreshSessionMetadata = useCallback(async () => {
    if (!sessionId) return;

    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}`, {
        method: "GET",
        headers: {
          Authorization: AUTH_HEADER,
          "Content-Type": "application/json",
        },
      });

      if (!res.ok) {
        return;
      }

      const data = (await res.json()) as GetSessionMetadataResponse;
      const session = data.session;
      setMetadata(session);
      setMetadataReady(true);
      const feedbackItems = Array.isArray(session.feedback_items)
        ? session.feedback_items
        : Array.isArray(session.feedback)
          ? session.feedback
          : [];
      registerMetadataFeedbackEvents(feedbackItems);
    } catch {
      return;
    }
  }, [registerMetadataFeedbackEvents, sessionId]);

  const progressChips = metadata?.progress_chips ?? [];
  const progressReady = metadataReady;
  const sessionState = metadata?.state ?? "UNKNOWN";

  // Initial metadata fetch when the page/session context is ready.
  useEffect(() => {
    setTimelineEvents([]);
    seenTimelineEventIdsRef.current.clear();
    seenFeedbackKeysRef.current.clear();
    setMetadataReady(false);
    void refreshSessionMetadata();
    void refreshTraceTimeline();
  }, [refreshSessionMetadata, refreshTraceTimeline]);

  // Poll metadata while provisioning/active so session transitions and timed hint unlocks
  // are reflected even if evaluator feedback polling is delayed or unavailable.
  useEffect(() => {
    if (!sessionId) return;
    const state = (metadata?.state ?? "").toUpperCase();
    if (state !== "PROVISIONING" && state !== "ACTIVE") return;

    let cancelled = false;
    let timeoutId: number | null = null;

    const tick = async () => {
      if (cancelled) return;
      await refreshSessionMetadata();
      if (cancelled) return;
      timeoutId = window.setTimeout(
        tick,
        jitterDelayMs(
          SESSION_METADATA_POLL_BASE_MS,
          SESSION_METADATA_POLL_JITTER_RATIO,
        ),
      );
    };

    void tick();

    return () => {
      cancelled = true; // Guard for in-flight work
      if (timeoutId !== null) window.clearTimeout(timeoutId); // This stops the polling
    };
  }, [sessionId, metadata?.state, refreshSessionMetadata]);

  return {
    metadata,
    setMetadata,
    progressReady,
    timelineEvents,
    feedbackError: null,
    feedbackLoading: false,
    feedbackReady: metadataReady,
    appendTimelineEvent,
    registerLearnerFeedbackEvents,
    refreshSessionMetadata,
    sessionState,
    progressChips,
  };
}
