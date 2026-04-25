import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useSessionStream } from "../hooks/useSessionStream";
import { FeedbackColumn } from "./session/components/FeedbackColumn";
import { LabGuideColumn } from "./session/components/LabGuideColumn";
import { SessionHeaderStatus } from "./session/components/SessionHeaderStatus";
import { SessionSuccessModal } from "./session/components/SessionSuccessModal";
import { WorkspaceColumn } from "./session/components/WorkspaceColumn";
import { formatTime } from "./session/helpers";
import { useFeedbackState } from "./session/hooks/useFeedbackState";
import { useHintsState } from "./session/hooks/useHintsState";
import { useSessionActions } from "./session/hooks/useSessionActions";
import { useSessionData } from "./session/hooks/useSessionData";
import { useSessionStreamIngestion } from "./session/hooks/useSessionStreamIngestion";
import { useTranscriptStreamView } from "./session/hooks/useTranscriptStreamView";
import type { AgentStatus } from "./session/types";
import { API_BASE, AUTH_HEADER } from "./session/ui";

export default function SessionPage() {
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("idle");
  const [isLeftCollapsed, setIsLeftCollapsed] = useState(false);
  const [isRightCollapsed, setIsRightCollapsed] = useState(false);
  const [stoppingSession, setStoppingSession] = useState(false);
  const [successModalDismissed, setSuccessModalDismissed] = useState(false);
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { connectionState, messages, sendPrompt } = useSessionStream(sessionId);

  const transcriptView = useTranscriptStreamView();
  const {
    transcriptEntries,
    setTranscriptEntries,
    activeEntry,
    isAwaitingResponse,
    setIsAwaitingResponse,
    activeEntryTsRef,
    pendingBufferRef,
    finalizePendingRef,
    resetActiveStream,
    ensureRevealLoop,
    transcriptViewportRef,
    onTranscriptScroll,
    onJumpToLatest,
    showJumpToLatest,
    activeTokens,
  } = transcriptView;

  const sessionData = useSessionData({ sessionId });
  const {
    metadata,
    setMetadata,
    progressReady,
    progressChips,
    timelineEvents,
    feedbackError,
    feedbackLoading,
    feedbackReady,
    appendTimelineEvent,
    registerLearnerFeedbackEvents,
    refreshSessionMetadata,
    sessionState,
  } = sessionData;

  const canSend =
    connectionState === "open" &&
    !isAwaitingResponse &&
    metadata?.completion_status !== "completed_success" &&
    (metadata?.interactive ?? false);
  const showSuccessModal =
    metadata?.completion_status === "completed_success" &&
    !successModalDismissed;

  useEffect(() => {
    if (metadata?.completion_status !== "completed_success") {
      setSuccessModalDismissed(false);
    }
  }, [metadata?.completion_status]);

  const sessionActions = useSessionActions({
    sessionId,
    canSend,
    interactionLocked: metadata?.completion_status === "completed_success",
    sendPrompt,
    setTranscriptEntries,
    setIsAwaitingResponse,
    resetActiveStream,
    setAgentStatus,
    refreshSessionMetadata,
  });
  const {
    prompt,
    setPrompt,
    onSubmitPrompt,
    emailFrom,
    emailSubject,
    emailBody,
    injectingEmail,
    injectEmailError,
    injectEmailResult,
    onSubmitEmail,
    onResetEmail,
    onEmailFromChange,
    onEmailSubjectChange,
    onEmailBodyChange,
    workspaceState,
    onToolSelect,
  } = sessionActions;

  useSessionStreamIngestion({
    messages,
    ensureRevealLoop,
    appendTimelineEvent,
    registerLearnerFeedbackEvents,
    activeEntryTsRef,
    pendingBufferRef,
    finalizePendingRef,
    setIsAwaitingResponse,
    setTranscriptEntries,
    setMetadata,
    setAgentStatus,
  });

  const { unlockedHints, hintsPanelOpen, hasUnreadHint, onHintsChipClick } =
    useHintsState({
      sessionId,
      hints: metadata?.hints,
      unreadHintCount: metadata?.unread_hint_count,
      refreshSessionMetadata,
      appendTimelineEvent,
    });
  const { feedbackItems, feedbackPanelOpen, onFeedbackChipClick } =
    useFeedbackState({
      sessionId,
      feedbackItems: metadata?.feedback_items,
      unreadFeedbackCount: metadata?.unread_feedback_count,
      refreshSessionMetadata,
    });

  const leftColumnTemplate = isLeftCollapsed ? "38px" : "minmax(280px, 20%)";
  const rightColumnTemplate = isRightCollapsed
    ? "38px"
    : "minmax(180px, 12.6%)";
  const canStopSession = ["CREATED", "PROVISIONING", "ACTIVE", "IDLE"].includes(
    sessionState.toUpperCase(),
  );

  const onStopSession = useCallback(async () => {
    if (!sessionId || stoppingSession || !canStopSession) {
      return;
    }

    setStoppingSession(true);
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/sessions/${sessionId}/stop`,
        {
          method: "POST",
          headers: {
            Authorization: AUTH_HEADER,
            "Content-Type": "application/json",
            "Idempotency-Key": `stop-session:${sessionId}`,
          },
        },
      );
      if (!response.ok) {
        appendTimelineEvent({
          id: `stop-failed-${Date.now()}`,
          timestamp: new Date().toISOString(),
          type: "system",
          granularity: "high",
          title: "Session stop failed",
          description: `Control plane returned HTTP ${response.status}.`,
          details:
            "Retry stopping the session. If this persists, check backend logs.",
          important: true,
        });
        return;
      }
      await refreshSessionMetadata();
      navigate("/labs");
    } catch {
      appendTimelineEvent({
        id: `stop-error-${Date.now()}`,
        timestamp: new Date().toISOString(),
        type: "system",
        granularity: "high",
        title: "Session stop request failed",
        description: "Could not reach control plane.",
        details:
          "Retry stopping the session. If this persists, check your network.",
        important: true,
      });
    } finally {
      setStoppingSession(false);
    }
  }, [
    appendTimelineEvent,
    canStopSession,
    navigate,
    refreshSessionMetadata,
    sessionId,
    stoppingSession,
  ]);

  return (
    <main
      style={{
        flex: "1 1 auto",
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
          minHeight: 40,
          alignItems: "center",
          zIndex: 20,
          overflow: "visible",
        }}
      >
        {progressReady && metadata ? (
          <div
            style={{
              width: "100%",
              animation: "headerChipsIn 220ms ease-out both",
            }}
          >
            <SessionHeaderStatus
              progressReady={progressReady}
              progressChips={progressChips}
              agentStatus={agentStatus}
              completionStatus={metadata.completion_status}
              completedAt={metadata.completed_at}
              completionReasonCode={metadata.completion_reason_code}
              unreadFeedbackCount={metadata.unread_feedback_count}
              feedbackItems={feedbackItems}
              feedbackPanelOpen={feedbackPanelOpen}
              onFeedbackChipClick={onFeedbackChipClick}
              hasUnreadHint={hasUnreadHint}
              unlockedHints={unlockedHints}
              hintsReady={progressReady}
              sessionState={sessionState}
              hintsPanelOpen={hintsPanelOpen}
              onHintsChipClick={onHintsChipClick}
              canStopSession={canStopSession}
              stoppingSession={stoppingSession}
              onStopSession={() => void onStopSession()}
            />
          </div>
        ) : (
          <div
            style={{
              width: "100%",
              height: 32,
              borderRadius: 8,
              background: "rgba(36, 43, 52, 0.28)",
              border: "1px solid rgba(74, 85, 98, 0.35)",
            }}
          />
        )}
        <style>{`
          @keyframes headerChipsIn {
            from { opacity: 0; transform: translateY(-2px); }
            to { opacity: 1; transform: translateY(0); }
          }
        `}</style>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: `${leftColumnTemplate} minmax(520px, 1fr) ${rightColumnTemplate}`,
          gridTemplateRows: "minmax(0, 1fr)",
          gap: 16,
          flex: "1 1 0%",
          minHeight: 0,
          overflow: "hidden",
          alignItems: "stretch",
          transition:
            "grid-template-columns 500ms cubic-bezier(0.22, 0.61, 0.36, 1)",
        }}
      >
        <aside
          style={{
            minHeight: 0,
            minWidth: 0,
            overflow: "hidden",
            position: "relative",
            border: "1px solid",
            borderColor: isLeftCollapsed ? "#d3dce5" : "transparent",
            borderRadius: 8,
            background: isLeftCollapsed ? "#f6f9fc" : "transparent",
            transition:
              "border-color 360ms ease, background-color 360ms ease, border-radius 360ms ease",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 0,
              overflow: "hidden",
              opacity: isLeftCollapsed ? 0 : 1,
              transition: "opacity 420ms ease",
              pointerEvents: isLeftCollapsed ? "none" : "auto",
            }}
          >
            <LabGuideColumn labId={metadata?.lab_id} />
          </div>

          <button
            type="button"
            onClick={() => setIsLeftCollapsed(true)}
            aria-label="Collapse lab guide"
            title="Collapse lab guide"
            style={{
              position: "absolute",
              top: 8,
              right: 24,
              zIndex: 2,
              appearance: "none",
              WebkitTapHighlightColor: "transparent",
              border: "1px solid #9bb0c5",
              borderRadius: 6,
              background: "#eef4fa",
              color: "#2a4258",
              padding: "2px 6px",
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 700,
              opacity: isLeftCollapsed ? 0 : 1,
              transition: "opacity 360ms ease",
              pointerEvents: isLeftCollapsed ? "none" : "auto",
            }}
          >
            ◂
          </button>

          <button
            type="button"
            onClick={() => setIsLeftCollapsed(false)}
            aria-label="Expand lab guide"
            title="Expand lab guide"
            style={{
              position: "absolute",
              inset: 0,
              appearance: "none",
              WebkitTapHighlightColor: "transparent",
              border: "none",
              background: "transparent",
              color: "#2a4258",
              cursor: "pointer",
              padding: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              writingMode: "vertical-rl",
              textOrientation: "mixed",
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: 0.4,
              opacity: isLeftCollapsed ? 1 : 0,
              transition: "opacity 420ms ease",
              pointerEvents: isLeftCollapsed ? "auto" : "none",
            }}
          >
            Lab Guide ▸
          </button>
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
            labId={metadata?.lab_id}
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
            injectingEmail={injectingEmail}
            sessionId={sessionId}
            injectEmailError={injectEmailError}
            injectEmailResult={injectEmailResult}
            onSubmitEmail={onSubmitEmail}
            onResetEmail={onResetEmail}
            onEmailFromChange={onEmailFromChange}
            onEmailSubjectChange={onEmailSubjectChange}
            onEmailBodyChange={onEmailBodyChange}
            onTranscriptScroll={onTranscriptScroll}
            showJumpToLatest={showJumpToLatest}
            onJumpToLatest={onJumpToLatest}
            prompt={prompt}
            canSend={canSend}
            interactionLocked={
              metadata?.completion_status === "completed_success"
            }
            onPromptChange={setPrompt}
            onSubmitPrompt={onSubmitPrompt}
            formatTime={formatTime}
          />
        </section>

        <aside
          style={{
            display: "flex",
            flexDirection: "column",
            position: "relative",
            minWidth: 0,
            height: "100%",
            minHeight: 0,
            maxHeight: "100%",
            overflow: "hidden",
            border: "1px solid",
            borderColor: "#d3dce5",
            borderRadius: 8,
            background: isRightCollapsed ? "#f6f9fc" : "transparent",
            transition:
              "border-color 360ms ease, background-color 360ms ease, border-radius 360ms ease",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 0,
              overflow: "hidden",
              opacity: isRightCollapsed ? 0 : 1,
              transition: "opacity 420ms ease",
              pointerEvents: isRightCollapsed ? "none" : "auto",
            }}
          >
            <FeedbackColumn
              feedbackLoading={feedbackLoading}
              feedbackReady={feedbackReady}
              feedbackError={feedbackError}
              timelineEvents={timelineEvents}
            />
          </div>

          <button
            type="button"
            onClick={() => setIsRightCollapsed(true)}
            aria-label="Collapse event timeline"
            title="Collapse event timeline"
            style={{
              position: "absolute",
              top: 8,
              left: 8,
              zIndex: 2,
              appearance: "none",
              WebkitTapHighlightColor: "transparent",
              border: "1px solid #9bb0c5",
              borderRadius: 6,
              background: "#eef4fa",
              color: "#2a4258",
              padding: "2px 6px",
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 700,
              opacity: isRightCollapsed ? 0 : 1,
              transition: "opacity 360ms ease",
              pointerEvents: isRightCollapsed ? "none" : "auto",
            }}
          >
            ▸
          </button>

          <button
            type="button"
            onClick={() => setIsRightCollapsed(false)}
            aria-label="Expand event timeline"
            title="Expand event timeline"
            style={{
              position: "absolute",
              inset: 0,
              appearance: "none",
              WebkitTapHighlightColor: "transparent",
              border: "none",
              background: "transparent",
              color: "#2a4258",
              cursor: "pointer",
              padding: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              writingMode: "vertical-lr",
              textOrientation: "mixed",
              fontSize: 12,
              fontWeight: 700,
              letterSpacing: 0.4,
              opacity: isRightCollapsed ? 1 : 0,
              transition: "opacity 420ms ease",
              pointerEvents: isRightCollapsed ? "auto" : "none",
            }}
          >
            ◂ Timeline
          </button>

          <div
            aria-hidden="true"
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              bottom: 0,
              height: 1,
              background: "#9bb0c5",
              pointerEvents: "none",
              zIndex: 4,
            }}
          />
        </aside>
      </div>
      {showSuccessModal ? (
        <SessionSuccessModal
          completedAt={metadata?.completed_at ?? null}
          onClose={() => setSuccessModalDismissed(true)}
        />
      ) : null}
    </main>
  );
}
