import { useState } from "react";
import { useParams } from "react-router-dom";
import { useSessionStream } from "../hooks/useSessionStream";
import { FeedbackColumn } from "./session/components/FeedbackColumn";
import { LabGuideColumn } from "./session/components/LabGuideColumn";
import { SessionHeaderStatus } from "./session/components/SessionHeaderStatus";
import { WorkspaceColumn } from "./session/components/WorkspaceColumn";
import { formatTime } from "./session/helpers";
import { useHintsState } from "./session/hooks/useHintsState";
import { useSessionActions } from "./session/hooks/useSessionActions";
import { useSessionData } from "./session/hooks/useSessionData";
import { useSessionStreamIngestion } from "./session/hooks/useSessionStreamIngestion";
import { useTranscriptStreamView } from "./session/hooks/useTranscriptStreamView";
import type { AgentStatus } from "./session/types";

export default function SessionPage() {
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("idle");
  const { sessionId } = useParams<{ sessionId: string }>();
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
    timelineEvents,
    feedbackError,
    feedbackLoading,
    appendTimelineEvent,
    registerLearnerFeedbackEvents,
    refreshSessionMetadata,
    sessionState,
    inboxComplete,
    contextComplete,
    tokenComplete,
  } = sessionData;

  const sessionActions = useSessionActions({
    sessionId,
    sendPrompt,
    setTranscriptEntries,
    setIsAwaitingResponse,
    resetActiveStream,
    setAgentStatus,
    appendTimelineEvent,
    refreshSessionMetadata,
  });
  const {
    prompt,
    setPrompt,
    onSubmitPrompt,
    emailFrom,
    emailSubject,
    emailBody,
    emailMalicious,
    injectingEmail,
    injectEmailError,
    injectEmailResult,
    onSubmitEmail,
    onResetEmail,
    onEmailFromChange,
    onEmailSubjectChange,
    onEmailBodyChange,
    onEmailMaliciousChange,
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

  const canSend =
    connectionState === "open" &&
    !isAwaitingResponse &&
    (metadata?.interactive ?? false);

  const { unlockedHints, hintsPanelOpen, hasUnreadHint, onHintsChipClick } =
    useHintsState({
      sessionId,
      sessionState: metadata?.state,
      appendTimelineEvent,
    });

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
        }}
      >
        <SessionHeaderStatus
          inboxComplete={inboxComplete}
          contextComplete={contextComplete}
          tokenComplete={tokenComplete}
          agentStatus={agentStatus}
          hasUnreadHint={hasUnreadHint}
          unlockedHints={unlockedHints}
          sessionState={sessionState}
          hintsPanelOpen={hintsPanelOpen}
          onHintsChipClick={onHintsChipClick}
        />
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns:
            "minmax(280px, 20%) minmax(520px, 1fr) minmax(300px, 23.3%)",
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
            onEmailFromChange={onEmailFromChange}
            onEmailSubjectChange={onEmailSubjectChange}
            onEmailBodyChange={onEmailBodyChange}
            onEmailMaliciousChange={onEmailMaliciousChange}
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
            height: "100%",
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
