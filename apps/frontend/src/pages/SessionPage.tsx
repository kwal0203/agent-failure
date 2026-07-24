import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useSessionStream } from "../hooks/useSessionStream";
import { useStopSessionMutation } from "../query/sessionMutations";
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

function SessionPageContent({ sessionId }: { sessionId?: string }) {
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("idle");
  const [isLeftCollapsed, setIsLeftCollapsed] = useState(false);
  const [isRightCollapsed, setIsRightCollapsed] = useState(false);
  const successAutoStopRequestedRef = useRef(false);
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
  } = transcriptView;

  const sessionData = useSessionData({ sessionId });
  const {
    metadata,
    progressReady,
    progressChips,
    timelineEvents,
    feedbackError,
    feedbackLoading,
    feedbackReady,
    registerLearnerFeedbackEvents,
    refreshSessionMetadata,
    refreshSessionTrace,
    sessionState,
    telemetryLogs,
    invoices,
  } = sessionData;

  const canSend =
    connectionState === "open" &&
    !isAwaitingResponse &&
    metadata?.completion_status !== "completed_success" &&
    (metadata?.interactive ?? false);
  const showSuccessModal = metadata?.completion_status === "completed_success";
  const stopSessionMutation = useStopSessionMutation(sessionId);
  const stoppingSession = stopSessionMutation.isPending;
  const stopSession = stopSessionMutation.mutateAsync;

  const sessionActions = useSessionActions({
    sessionId,
    canSend,
    interactionLocked: metadata?.completion_status === "completed_success",
    sendPrompt,
    setTranscriptEntries,
    setIsAwaitingResponse,
    resetActiveStream,
    setAgentStatus,
  });
  const {
    prompt,
    setPrompt,
    onSubmitPrompt,
    emailFrom,
    emailSubject,
    emailBody,
    injectingEmail,
    fromValidationError,
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
    registerLearnerFeedbackEvents,
    activeEntryTsRef,
    pendingBufferRef,
    finalizePendingRef,
    setIsAwaitingResponse,
    setTranscriptEntries,
    setAgentStatus,
    refreshSessionMetadata,
    refreshSessionTrace,
  });

  const { unlockedHints, hintsPanelOpen, hasUnreadHint, onHintsChipClick } =
    useHintsState({
      sessionId,
      hints: metadata?.hints,
      unreadHintCount: metadata?.unread_hint_count,
    });
  const { feedbackItems, feedbackPanelOpen, onFeedbackChipClick } =
    useFeedbackState({
      sessionId,
      feedbackItems: metadata?.feedback_items,
      unreadFeedbackCount: metadata?.unread_feedback_count,
    });

  const leftColumnTemplate = isLeftCollapsed ? "38px" : "minmax(280px, 20%)";
  const rightColumnTemplate = isRightCollapsed
    ? "38px"
    : "minmax(180px, 12.6%)";
  const canStopSession = ["CREATED", "PROVISIONING", "ACTIVE", "IDLE"].includes(
    sessionState.toUpperCase(),
  );

  const onStopSession = useCallback(
    async (navigateAfterStop = true, force = false) => {
      if (!sessionId || stoppingSession || (!force && !canStopSession)) {
        return;
      }

      try {
        await stopSession();
        if (navigateAfterStop) {
          navigate("/labs");
        }
      } catch {
        return;
      }
    },
    [canStopSession, navigate, sessionId, stopSession, stoppingSession],
  );

  useEffect(() => {
    if (
      metadata?.completion_status !== "completed_success" ||
      successAutoStopRequestedRef.current
    ) {
      return;
    }
    successAutoStopRequestedRef.current = true;
    void onStopSession(false, true);
  }, [metadata?.completion_status, onStopSession]);

  return (
    <main className="flex min-h-0 flex-1 flex-col overflow-hidden px-4 pb-2 pt-4">
      <header className="relative z-20 mb-4 flex min-h-10 flex-none items-center overflow-visible">
        {progressReady && metadata ? (
          <div className="w-full animate-[headerChipsIn_220ms_ease-out_both]">
            <SessionHeaderStatus
              progressReady={progressReady}
              progressChips={progressChips}
              agentStatus={agentStatus}
              completionStatus={metadata.completion_status}
              completedAt={metadata.completed_at ?? null}
              completionReasonCode={metadata.completion_reason_code ?? null}
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
          <div className="h-8 w-full rounded-lg border border-slate-600/35 bg-slate-700/25" />
        )}
        <style>{`
          @keyframes headerChipsIn {
            from { opacity: 0; transform: translateY(-2px); }
            to { opacity: 1; transform: translateY(0); }
          }
        `}</style>
      </header>

      <div
        className="grid min-h-0 flex-[1_1_0%] items-stretch gap-4 overflow-hidden transition-[grid-template-columns] duration-500 ease-[cubic-bezier(0.22,0.61,0.36,1)]"
        style={{
          gridTemplateColumns: `${leftColumnTemplate} minmax(520px, 1fr) ${rightColumnTemplate}`,
          gridTemplateRows: "minmax(0, 1fr)",
        }}
      >
        <aside
          className={`relative min-h-0 min-w-0 overflow-hidden rounded-lg border transition-[border-color,background-color,border-radius] duration-300 ${
            isLeftCollapsed
              ? "border-slate-300 bg-slate-100/90"
              : "border-transparent bg-transparent"
          }`}
        >
          <div
            className="absolute inset-0 overflow-hidden transition-opacity duration-[420ms]"
            style={{
              opacity: isLeftCollapsed ? 0 : 1,
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
            className="absolute right-6 top-2 z-[2] appearance-none rounded-md border border-slate-400 bg-slate-100 px-1.5 py-0.5 text-xs font-bold text-slate-700 transition-opacity duration-300 [webkit-tap-highlight-color:transparent]"
            style={{
              opacity: isLeftCollapsed ? 0 : 1,
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
            className="absolute inset-0 flex appearance-none items-center justify-center bg-transparent p-0 text-xs font-bold tracking-[0.4px] text-slate-700 transition-opacity duration-[420ms] [text-orientation:mixed] [webkit-tap-highlight-color:transparent] [writing-mode:vertical-rl]"
            style={{
              opacity: isLeftCollapsed ? 1 : 0,
              pointerEvents: isLeftCollapsed ? "auto" : "none",
            }}
          >
            Lab Guide ▸
          </button>
        </aside>

        <section className="flex min-h-0 min-w-0 overflow-hidden">
          <WorkspaceColumn
            labId={metadata?.lab_id}
            transcriptViewportRef={transcriptViewportRef}
            transcriptEntries={transcriptEntries}
            activeEntry={activeEntry}
            isAwaitingResponse={isAwaitingResponse}
            selectedTool={workspaceState.selectedTool}
            toolPaneOpen={workspaceState.toolPaneOpen}
            onToolSelect={onToolSelect}
            emailFrom={emailFrom}
            emailSubject={emailSubject}
            emailBody={emailBody}
            injectingEmail={injectingEmail}
            sessionId={sessionId}
            fromValidationError={fromValidationError}
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
            telemetryLogs={telemetryLogs}
            invoices={invoices}
            runtimeFiles={metadata?.runtime_files ?? []}
          />
        </section>

        <aside
          className={`relative flex h-full min-h-0 min-w-0 max-h-full flex-col overflow-hidden rounded-lg border transition-[border-color,background-color,border-radius] duration-300 ${
            isRightCollapsed
              ? "border-slate-300 bg-slate-100/90"
              : "border-slate-300/90 bg-transparent"
          }`}
        >
          <div
            className="absolute inset-0 overflow-hidden transition-opacity duration-[420ms]"
            style={{
              opacity: isRightCollapsed ? 0 : 1,
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
            className="absolute left-2 top-2 z-[2] appearance-none rounded-md border border-slate-400 bg-slate-100 px-1.5 py-0.5 text-xs font-bold text-slate-700 transition-opacity duration-300 [webkit-tap-highlight-color:transparent]"
            style={{
              opacity: isRightCollapsed ? 0 : 1,
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
            className="absolute inset-0 flex appearance-none items-center justify-center bg-transparent p-0 text-xs font-bold tracking-[0.4px] text-slate-700 transition-opacity duration-[420ms] [text-orientation:mixed] [webkit-tap-highlight-color:transparent] [writing-mode:vertical-lr]"
            style={{
              opacity: isRightCollapsed ? 1 : 0,
              pointerEvents: isRightCollapsed ? "auto" : "none",
            }}
          >
            ◂ Timeline
          </button>

          <div
            aria-hidden="true"
            className="pointer-events-none absolute bottom-0 left-0 right-0 z-[4] h-px bg-slate-400"
          />
        </aside>
      </div>
      {showSuccessModal ? (
        <SessionSuccessModal
          completedAt={metadata?.completed_at ?? null}
          onReturnToCatalog={() => navigate("/labs")}
        />
      ) : null}
    </main>
  );
}

export default function SessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  return (
    <SessionPageContent
      key={sessionId ?? "missing-session"}
      sessionId={sessionId}
    />
  );
}
