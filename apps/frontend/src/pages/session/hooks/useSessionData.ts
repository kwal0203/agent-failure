import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  SESSION_METADATA_POLL_BASE_MS,
  SESSION_METADATA_POLL_JITTER_RATIO,
} from "../constants";
import { jitterDelayMs } from "../helpers";
import type {
  GetFeedbackResponse,
  GetSessionMetadataResponse,
  GetSessionTraceResponse,
  LearnerFeedbackItem,
  SessionMetadata,
  SessionProgressChip,
  SessionTraceEvent,
  TimelineEvent,
} from "../types";
import {
  API_BASE,
  AUTH_HEADER,
  formatStatusLabel,
  humanizeReasonCode,
} from "../ui";

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

const FEEDBACK_LOADING_SHOW_DELAY_MS = 200;
const FEEDBACK_LOADING_MIN_VISIBLE_MS = 300;

function formatPersistedTraceTitle(event: SessionTraceEvent): string {
  const toolName = event.payload.tool_name;
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
  return event.event_type;
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
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackReady, setFeedbackReady] = useState(false);
  const feedbackLoadingShowTimerRef = useRef<number | null>(null);
  const feedbackLoadingVisibleSinceRef = useRef<number | null>(null);

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
      setMetadata(data.session);
      setMetadataReady(true);
    } catch {
      return;
    }
  }, [sessionId]);

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
    (feedback: LearnerFeedbackItem[], timestamp: string) => {
      for (const item of feedback) {
        const key = `${item.status}|${item.reason_code}|${item.evidence_snippet}`;
        if (seenFeedbackKeysRef.current.has(key)) continue;
        seenFeedbackKeysRef.current.add(key);
        appendTimelineEvent({
          id: `feedback-${key}`,
          timestamp,
          type: "explanation",
          granularity: "high",
          title: humanizeReasonCode(item.reason_code),
          description: "Placeholder",
          details: `Feedback status: ${formatStatusLabel(item.status)}`,
          important: item.status === "learned",
        });
      }
    },
    [appendTimelineEvent],
  );

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

  // Load evaluator feedback once and then poll in the background to append new events.
  useEffect(() => {
    if (!sessionId) return;

    let cancelled = false;
    let timeoutId: number | null = null;
    setFeedbackReady(false);
    const beginForegroundLoading = () => {
      if (feedbackLoadingShowTimerRef.current !== null) {
        window.clearTimeout(feedbackLoadingShowTimerRef.current);
      }
      feedbackLoadingVisibleSinceRef.current = null;
      feedbackLoadingShowTimerRef.current = window.setTimeout(() => {
        if (cancelled) return;
        feedbackLoadingVisibleSinceRef.current = Date.now();
        setFeedbackLoading(true);
        feedbackLoadingShowTimerRef.current = null;
      }, FEEDBACK_LOADING_SHOW_DELAY_MS);
    };
    const endForegroundLoading = () => {
      if (feedbackLoadingShowTimerRef.current !== null) {
        window.clearTimeout(feedbackLoadingShowTimerRef.current);
        feedbackLoadingShowTimerRef.current = null;
      }

      const visibleSince = feedbackLoadingVisibleSinceRef.current;
      if (visibleSince === null) {
        setFeedbackLoading(false);
        return;
      }

      const elapsed = Date.now() - visibleSince;
      const remaining = FEEDBACK_LOADING_MIN_VISIBLE_MS - elapsed;
      if (remaining > 0) {
        window.setTimeout(() => {
          if (cancelled) return;
          setFeedbackLoading(false);
          feedbackLoadingVisibleSinceRef.current = null;
        }, remaining);
        return;
      }

      setFeedbackLoading(false);
      feedbackLoadingVisibleSinceRef.current = null;
    };
    const run = async (opts?: { background?: boolean }) => {
      if (!opts?.background) {
        beginForegroundLoading();
        setFeedbackError(null);
      }

      try {
        const res = await fetch(
          `${API_BASE}/api/v1/sessions/${sessionId}/evaluator-feedback`,
          {
            method: "GET",
            headers: {
              Authorization: AUTH_HEADER,
              "Content-Type": "application/json",
            },
          },
        );

        if (!res.ok) {
          if (!cancelled && !opts?.background) {
            setFeedbackError(`HTTP ${res.status}`);
          }
          return;
        }

        const data = (await res.json()) as GetFeedbackResponse;
        if (!cancelled) {
          registerLearnerFeedbackEvents(
            data.feedback,
            new Date().toISOString(),
          );
          await refreshSessionMetadata();
        }
      } catch (e) {
        if (!cancelled && !opts?.background) {
          setFeedbackError(e instanceof Error ? e.message : "request failed");
        }
      } finally {
        if (!cancelled && !opts?.background) {
          endForegroundLoading();
          setFeedbackReady(true);
        }
      }
    };

    void run();

    const tick = async () => {
      if (cancelled) return;
      await run({ background: true });
      if (cancelled) return;
      timeoutId = window.setTimeout(
        tick,
        jitterDelayMs(
          SESSION_METADATA_POLL_BASE_MS,
          SESSION_METADATA_POLL_JITTER_RATIO,
        ),
      );
    };
    timeoutId = window.setTimeout(
      tick,
      jitterDelayMs(
        SESSION_METADATA_POLL_BASE_MS,
        SESSION_METADATA_POLL_JITTER_RATIO,
      ),
    );

    return () => {
      cancelled = true;
      if (timeoutId !== null) window.clearTimeout(timeoutId);
      if (feedbackLoadingShowTimerRef.current !== null) {
        window.clearTimeout(feedbackLoadingShowTimerRef.current);
        feedbackLoadingShowTimerRef.current = null;
      }
    };
  }, [sessionId, refreshSessionMetadata, registerLearnerFeedbackEvents]);

  return {
    metadata,
    setMetadata,
    progressReady,
    timelineEvents,
    feedbackError,
    feedbackLoading,
    feedbackReady,
    appendTimelineEvent,
    registerLearnerFeedbackEvents,
    refreshSessionMetadata,
    sessionState,
    progressChips,
  };
}
