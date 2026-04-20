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
  LearnerFeedbackItem,
  SessionMetadata,
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
  inboxComplete: boolean;
  contextComplete: boolean;
  tokenComplete: boolean;
};

const FEEDBACK_LOADING_SHOW_DELAY_MS = 200;
const FEEDBACK_LOADING_MIN_VISIBLE_MS = 300;

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
  const inboxComplete = progressChips.some(
    (chip) =>
      chip.objective_key === "malicious_email_injected" &&
      chip.status === "complete",
  );
  const contextComplete = progressChips.some(
    (chip) =>
      chip.objective_key === "malicious_instructions_entered_context" &&
      chip.status === "complete",
  );
  const tokenComplete = progressChips.some(
    (chip) =>
      chip.objective_key === "token_exposed" && chip.status === "complete",
  );

  // Initial metadata fetch when the page/session context is ready.
  useEffect(() => {
    setMetadataReady(false);
    void refreshSessionMetadata();
  }, [refreshSessionMetadata]);

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
    inboxComplete,
    contextComplete,
    tokenComplete,
  };
}
