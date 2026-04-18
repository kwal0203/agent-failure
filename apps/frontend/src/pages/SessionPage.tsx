import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useSessionStream } from "../hooks/useSessionStream";
import { FeedbackColumn } from "./session/components/FeedbackColumn";
import { LabGuideColumn } from "./session/components/LabGuideColumn";
import { SessionHeaderStatus } from "./session/components/SessionHeaderStatus";
import { WorkspaceColumn } from "./session/components/WorkspaceColumn";
import {
  HINT_CATALOG,
  HINT_UNLOCK_SCHEDULE_MS,
  SESSION_METADATA_POLL_BASE_MS,
  SESSION_METADATA_POLL_JITTER_RATIO,
} from "./session/constants";
import { formatTime, jitterDelayMs } from "./session/helpers";
import type {
  AgentStatus,
  GetFeedbackResponse,
  GetSessionMetadataResponse,
  InjectSessionEmailResponse,
  LearnerFeedbackItem,
  SessionMetadata,
  SessionWorkspaceState,
  TimelineEvent,
  ToolKey,
  TranscriptEntry,
  UnlockedHint,
} from "./session/types";
import {
  API_BASE,
  AUTH_HEADER,
  formatStatusLabel,
  humanizeReasonCode,
} from "./session/ui";

export default function SessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { connectionState, messages, sendPrompt } = useSessionStream(sessionId);
  const processedMessageCount = useRef(0);
  const transcriptViewportRef = useRef<HTMLDivElement | null>(null);
  const activeEntryTsRef = useRef<string | null>(null);
  const displayedEntryRef = useRef("");
  const pendingBufferRef = useRef("");
  const finalizePendingRef = useRef(false);
  const animationFrameRef = useRef<number | null>(null);
  const lastRevealAtMsRef = useRef(0);
  const [metadata, setMetadata] = useState<SessionMetadata | null>(null);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [transcriptEntries, setTranscriptEntries] = useState<TranscriptEntry[]>(
    [],
  );
  const [activeEntry, setActiveEntry] = useState("");
  const [isAwaitingResponse, setIsAwaitingResponse] = useState(false);
  const [emailFrom, setEmailFrom] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");
  const [emailMalicious, setEmailMalicious] = useState(true);
  const [injectingEmail, setInjectingEmail] = useState(false);
  const [injectEmailError, setInjectEmailError] = useState<string | null>(null);
  const [injectEmailResult, setInjectEmailResult] = useState<string | null>(
    null,
  );
  const [workspaceState, setWorkspaceState] = useState<SessionWorkspaceState>({
    selectedTool: null,
    toolPaneOpen: false,
    transcriptAutoScrollEnabled: true,
  });
  const [showJumpToLatest, setShowJumpToLatest] = useState(false);
  const transcriptContentSnapshotRef = useRef({ entries: 0, activeLength: 0 });
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const seenTimelineEventIdsRef = useRef(new Set<string>());
  const seenFeedbackKeysRef = useRef(new Set<string>());
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("idle");
  const [unlockedHints, setUnlockedHints] = useState<UnlockedHint[]>([]);
  const [hintsPanelOpen, setHintsPanelOpen] = useState(false);
  const [hasUnreadHint, setHasUnreadHint] = useState(false);
  const hintsStartedAtRef = useRef<number | null>(null);
  const nextHintIndexRef = useRef(0);

  const resetActiveStream = useCallback(() => {
    displayedEntryRef.current = "";
    pendingBufferRef.current = "";
    finalizePendingRef.current = false;
    activeEntryTsRef.current = null;
    setActiveEntry("");
    if (animationFrameRef.current !== null) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
  }, []);

  const drainRevealFrame = useCallback(() => {
    const revealIntervalMs = 60;
    const now = performance.now();
    if (now - lastRevealAtMsRef.current < revealIntervalMs) {
      animationFrameRef.current = requestAnimationFrame(drainRevealFrame);
      return;
    }

    if (pendingBufferRef.current.length > 0) {
      const buffer = pendingBufferRef.current;
      const match = buffer.match(/^(\s*\S+\s*)/);
      const reveal = match ? match[1] : buffer;
      pendingBufferRef.current = buffer.slice(reveal.length);
      displayedEntryRef.current += reveal;
      lastRevealAtMsRef.current = now;
      setActiveEntry(displayedEntryRef.current);
      animationFrameRef.current = requestAnimationFrame(drainRevealFrame);
      return;
    }

    if (finalizePendingRef.current) {
      const finalized = displayedEntryRef.current.trim();
      if (finalized) {
        setTranscriptEntries((entries) => {
          const last = entries.length > 0 ? entries[entries.length - 1] : null;
          if (
            last &&
            last.role === "agent" &&
            last.content === finalized &&
            last.timestamp ===
              (activeEntryTsRef.current ?? new Date().toISOString())
          ) {
            return entries;
          }
          return [
            ...entries,
            {
              role: "agent",
              content: finalized,
              timestamp: activeEntryTsRef.current ?? new Date().toISOString(),
            },
          ];
        });
      }
      resetActiveStream();
      setIsAwaitingResponse(false);
      return;
    }

    animationFrameRef.current = null;
  }, [resetActiveStream]);

  const ensureRevealLoop = useCallback(() => {
    if (animationFrameRef.current === null) {
      animationFrameRef.current = requestAnimationFrame(drainRevealFrame);
    }
  }, [drainRevealFrame]);

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
    } catch {
      return;
    }
  }, [sessionId]);

  // Initial metadata fetch when the page/session context is ready.
  useEffect(() => {
    void refreshSessionMetadata();
  }, [refreshSessionMetadata]);

  // Poll metadata while provisioning so session state transitions are reflected in UI.
  useEffect(() => {
    if (!sessionId) return;
    if (metadata?.state !== "PROVISIONING") return;

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
    const run = async (opts?: { background?: boolean }) => {
      if (!opts?.background) {
        setFeedbackLoading(true);
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
          setFeedbackLoading(false);
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
    };
  }, [sessionId, refreshSessionMetadata, registerLearnerFeedbackEvents]);

  // Consume newly streamed backend messages and map them into transcript, timeline, and status state.
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
        appendTimelineEvent({
          id: `status-${message.timestamp}-${message.payload.state}-${message.payload.runtime_substate ?? "none"}`,
          timestamp: message.timestamp,
          type: "system",
          granularity: "high",
          title: "Session status updated",
          description: `${message.payload.state}${message.payload.runtime_substate ? ` · ${message.payload.runtime_substate}` : ""}`,
        });
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
          appendTimelineEvent({
            id: `agent-final-${message.timestamp}`,
            timestamp: message.timestamp,
            type: "agent_action",
            granularity: "detailed",
            title: "Agent response completed",
            description: "A streamed response finished in the transcript.",
          });
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
        appendTimelineEvent({
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
          setAgentStatus("active");
          continue;
        }
        setTranscriptEntries((entries) => [
          ...entries,
          {
            role: "system",
            content: `[${message.payload.event_code}] ${message.payload.message}`,
            timestamp: message.timestamp,
          },
        ]);
        appendTimelineEvent({
          id: `trace-${message.timestamp}-${message.payload.event_code}`,
          timestamp: message.timestamp,
          type: message.payload.event_code.includes("TOOL")
            ? "tool_call"
            : "system",
          granularity: "detailed",
          title: message.payload.event_code,
          description: message.payload.message,
        });
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
        appendTimelineEvent({
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
    appendTimelineEvent,
    registerLearnerFeedbackEvents,
  ]);

  const onSubmitPrompt = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const text = prompt.trim();
    if (!text) return;
    setTranscriptEntries((entries) => [
      ...entries,
      {
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
      },
    ]);
    resetActiveStream();
    setIsAwaitingResponse(true);
    setAgentStatus("active");
    sendPrompt(text);
    setPrompt("");
  };

  const onSubmitEmail = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!sessionId) return;

    const sender = emailFrom.trim();
    const subject = emailSubject.trim();
    const body = emailBody.trim();
    if (!sender || !subject || !body) {
      setInjectEmailError("From, subject, and body are required.");
      return;
    }

    setInjectingEmail(true);
    setInjectEmailError(null);
    setInjectEmailResult(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/sessions/${sessionId}/inbox/email`,
        {
          method: "POST",
          headers: {
            Authorization: AUTH_HEADER,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email_from: sender,
            email_subject: subject,
            email_body: body,
            malicious: emailMalicious,
            source: "learner",
          }),
        },
      );

      const payload = (await res.json()) as
        | InjectSessionEmailResponse
        | { error?: { message?: string } };
      if (!res.ok) {
        const msg =
          "error" in payload && payload.error?.message
            ? payload.error.message
            : `HTTP ${res.status}`;
        setInjectEmailError(msg);
        appendTimelineEvent({
          id: `email-inject-error-${new Date().toISOString()}-${res.status}`,
          timestamp: new Date().toISOString(),
          type: "system",
          granularity: "high",
          title: "Email injection failed",
          description: msg,
          important: true,
        });
        return;
      }

      const accepted =
        "accepted" in payload && payload.accepted ? "accepted" : "submitted";
      const emailId =
        "email_id" in payload && payload.email_id
          ? ` (id: ${payload.email_id})`
          : "";
      setInjectEmailResult(`Email ${accepted}${emailId}.`);
      appendTimelineEvent({
        id: `email-inject-${new Date().toISOString()}-${sender}-${subject}`,
        timestamp: new Date().toISOString(),
        type: "attacker_action",
        granularity: "high",
        title: "Email injected to inbox",
        description: `Email ${accepted}${emailId}.`,
        details: `From: ${sender}\nSubject: ${subject}`,
      });
      await refreshSessionMetadata();
    } catch (err) {
      const message = err instanceof Error ? err.message : "request failed";
      setInjectEmailError(message);
      appendTimelineEvent({
        id: `email-inject-error-${new Date().toISOString()}-exception`,
        timestamp: new Date().toISOString(),
        type: "system",
        granularity: "high",
        title: "Email injection failed",
        description: message,
        important: true,
      });
    } finally {
      setInjectingEmail(false);
    }
  };

  const onResetEmail = () => {
    setEmailFrom("");
    setEmailSubject("");
    setEmailBody("");
    setEmailMalicious(true);
    setInjectEmailError(null);
    setInjectEmailResult(null);
  };

  const canSend =
    connectionState === "open" &&
    !isAwaitingResponse &&
    (metadata?.interactive ?? false);

  const onToolSelect = (tool: ToolKey) => {
    setWorkspaceState((prev) => {
      if (prev.toolPaneOpen && prev.selectedTool === tool) {
        return {
          ...prev,
          toolPaneOpen: false,
        };
      }
      return {
        ...prev,
        selectedTool: tool,
        toolPaneOpen: true,
      };
    });
  };

  const scrollTranscriptToBottom = useCallback(() => {
    const viewport = transcriptViewportRef.current;
    if (!viewport) return;
    viewport.scrollTop = viewport.scrollHeight;
  }, []);

  const onTranscriptScroll = useCallback(() => {
    const viewport = transcriptViewportRef.current;
    if (!viewport) return;
    const remaining =
      viewport.scrollHeight - viewport.clientHeight - viewport.scrollTop;
    const nearBottom = remaining <= 48;

    setWorkspaceState((prev) => {
      if (prev.transcriptAutoScrollEnabled === nearBottom) {
        return prev;
      }
      return {
        ...prev,
        transcriptAutoScrollEnabled: nearBottom,
      };
    });

    if (nearBottom) {
      setShowJumpToLatest(false);
    }
  }, []);

  const onJumpToLatest = useCallback(() => {
    scrollTranscriptToBottom();
    setWorkspaceState((prev) => ({
      ...prev,
      transcriptAutoScrollEnabled: true,
    }));
    setShowJumpToLatest(false);
  }, [scrollTranscriptToBottom]);

  // Reset hint-unlock state whenever the learner switches to a different session.
  useEffect(() => {
    if (!sessionId) return;
    hintsStartedAtRef.current = null;
    nextHintIndexRef.current = 0;
    setUnlockedHints([]);
    setHasUnreadHint(false);
    setHintsPanelOpen(false);
  }, [sessionId]);

  // Start and run the timed hint unlock scheduler while the session is ACTIVE.
  useEffect(() => {
    if ((metadata?.state ?? "").toUpperCase() !== "ACTIVE") return;
    if (nextHintIndexRef.current >= HINT_CATALOG.length) return;
    if (hintsStartedAtRef.current === null) {
      hintsStartedAtRef.current = Date.now();
    }

    const intervalId = window.setInterval(() => {
      const startedAt = hintsStartedAtRef.current;
      if (startedAt === null) return;

      const elapsedMs = Date.now() - startedAt;
      while (nextHintIndexRef.current < HINT_CATALOG.length) {
        const hintIndex = nextHintIndexRef.current;
        const unlockAtMs =
          HINT_UNLOCK_SCHEDULE_MS[hintIndex] ?? Number.MAX_SAFE_INTEGER;
        if (elapsedMs < unlockAtMs) break;

        const hintText = HINT_CATALOG[hintIndex];
        const unlockedAt = new Date().toISOString();
        setUnlockedHints((prev) => {
          if (prev.some((item) => item.index === hintIndex)) {
            return prev;
          }
          return [
            ...prev,
            {
              index: hintIndex,
              text: hintText,
              unlockedAt,
            },
          ];
        });
        setHasUnreadHint(true);
        appendTimelineEvent({
          id: `hint-unlocked-${hintIndex}-${unlockedAt}`,
          timestamp: unlockedAt,
          type: "explanation",
          granularity: "high",
          title: `Hint ${hintIndex + 1} unlocked`,
          description: "A new hint is available from the Hints chip.",
        });
        nextHintIndexRef.current += 1;
      }
    }, 1000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [appendTimelineEvent, metadata?.state]);

  const activeTokens = activeEntry.match(/(\s+|\S+)/g) ?? [];
  const currentState = metadata?.state ?? "UNKNOWN";
  const progressChips = metadata?.progress_chips ?? [];
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

  const onHintsChipClick = () => {
    setHintsPanelOpen((prev) => !prev);
    setHasUnreadHint(false);
  };

  // Keep transcript pinned to bottom when auto-scroll is enabled; otherwise show jump-to-latest affordance.
  useEffect(() => {
    const nextSnapshot = {
      entries: transcriptEntries.length,
      activeLength: activeEntry.length,
    };
    const previous = transcriptContentSnapshotRef.current;
    const hasNewTranscriptContent =
      nextSnapshot.entries > previous.entries ||
      nextSnapshot.activeLength > previous.activeLength;

    transcriptContentSnapshotRef.current = nextSnapshot;
    if (!hasNewTranscriptContent) return;

    if (workspaceState.transcriptAutoScrollEnabled) {
      scrollTranscriptToBottom();
      setShowJumpToLatest(false);
      return;
    }

    setShowJumpToLatest(true);
  }, [
    transcriptEntries,
    activeEntry,
    workspaceState.transcriptAutoScrollEnabled,
    scrollTranscriptToBottom,
  ]);

  // Ensure the transcript starts at latest content on initial mount.
  useEffect(() => {
    scrollTranscriptToBottom();
  }, [scrollTranscriptToBottom]);

  // Cleanup any pending animation frame on unmount to avoid leaks.
  useEffect(() => {
    return () => {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return (
    <main
      style={{
        height: "100%",
        minHeight: 0,
        padding: "16px 16px 8px",
        boxSizing: "border-box",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <header
        style={{
          flex: "0 0 auto",
          marginBottom: 16,
          position: "relative",
          display: "flex",
        }}
      >
        <SessionHeaderStatus
          inboxComplete={inboxComplete}
          contextComplete={contextComplete}
          tokenComplete={tokenComplete}
          agentStatus={agentStatus}
          hasUnreadHint={hasUnreadHint}
          unlockedHints={unlockedHints}
          sessionState={currentState}
          hintsPanelOpen={hintsPanelOpen}
          onHintsChipClick={onHintsChipClick}
        />
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "minmax(280px, 24%) minmax(520px, 1fr) minmax(300px, 28%)",
          gridTemplateRows: "minmax(0, 1fr)",
          gap: 16,
          flex: "1 1 0%",
          minHeight: 0,
          overflow: "hidden",
          alignItems: "stretch",
        }}
      >
        <aside style={{ minHeight: 0, overflow: "hidden" }}>
          <LabGuideColumn />
        </aside>

        <section
          style={{
            display: "flex",
            minHeight: 0,
            minWidth: 0,
            overflow: "hidden",
          }}
        >
          <WorkspaceColumn
            transcriptViewportRef={transcriptViewportRef}
            transcriptEntries={transcriptEntries}
            activeEntry={activeEntry}
            activeTokens={activeTokens}
            isAwaitingResponse={isAwaitingResponse}
            selectedTool={workspaceState.selectedTool}
            toolPaneOpen={workspaceState.toolPaneOpen}
            onToolSelect={onToolSelect}
            emailFrom={emailFrom}
            emailSubject={emailSubject}
            emailBody={emailBody}
            emailMalicious={emailMalicious}
            injectingEmail={injectingEmail}
            sessionId={sessionId}
            injectEmailError={injectEmailError}
            injectEmailResult={injectEmailResult}
            onSubmitEmail={onSubmitEmail}
            onResetEmail={onResetEmail}
            onEmailFromChange={setEmailFrom}
            onEmailSubjectChange={setEmailSubject}
            onEmailBodyChange={setEmailBody}
            onEmailMaliciousChange={setEmailMalicious}
            onTranscriptScroll={onTranscriptScroll}
            showJumpToLatest={showJumpToLatest}
            onJumpToLatest={onJumpToLatest}
            prompt={prompt}
            canSend={canSend}
            onPromptChange={setPrompt}
            onSubmitPrompt={onSubmitPrompt}
            formatTime={formatTime}
          />
        </section>

        <aside
          style={{
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
            maxHeight: "100%",
            overflow: "hidden",
          }}
        >
          <FeedbackColumn
            feedbackLoading={feedbackLoading}
            feedbackError={feedbackError}
            timelineEvents={timelineEvents}
          />
        </aside>
      </div>
    </main>
  );
}
