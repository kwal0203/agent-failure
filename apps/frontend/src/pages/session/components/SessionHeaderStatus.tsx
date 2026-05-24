import {
  agentStatusTone,
  formatTime,
  hintTone,
  objectiveTone,
  statusChipStyle,
} from "../helpers";
import type {
  AgentStatus,
  SessionCompletionStatus,
  SessionFeedbackItem,
  SessionProgressChip,
  UnlockedHint,
} from "../types";
import { statusTone } from "../ui";
import { FeedbackPopover } from "./FeedbackPopover";
import { SessionCompletionIndicator } from "./SessionCompletionIndicator";

type ProgressStatusHeaderProps = {
  progressReady: boolean;
  progressChips: SessionProgressChip[];
};

type SessionStatusHeaderProps = {
  agentStatus: AgentStatus;
  completionStatus: SessionCompletionStatus;
  completedAt: string | null;
  completionReasonCode: string | null;
  unreadFeedbackCount: number;
  feedbackItems: SessionFeedbackItem[];
  feedbackPanelOpen: boolean;
  onFeedbackChipClick: () => void;
  hasUnreadHint: boolean;
  unlockedHints: UnlockedHint[];
  hintsReady: boolean;
  sessionState: string;
  hintsPanelOpen: boolean;
  onHintsChipClick: () => void;
  canStopSession: boolean;
  stoppingSession: boolean;
  onStopSession: () => void;
};

type SessionHeaderStatusProps = {
  progressReady: boolean;
  progressChips: SessionProgressChip[];
  agentStatus: AgentStatus;
  completionStatus: SessionCompletionStatus;
  completedAt: string | null;
  completionReasonCode: string | null;
  unreadFeedbackCount: number;
  feedbackItems: SessionFeedbackItem[];
  feedbackPanelOpen: boolean;
  onFeedbackChipClick: () => void;
  hasUnreadHint: boolean;
  unlockedHints: UnlockedHint[];
  hintsReady: boolean;
  sessionState: string;
  hintsPanelOpen: boolean;
  onHintsChipClick: () => void;
  canStopSession: boolean;
  stoppingSession: boolean;
  onStopSession: () => void;
};

export function ProgressStatusHeader({
  progressReady,
  progressChips,
}: ProgressStatusHeaderProps) {
  if (!progressReady) {
    const placeholderStyle = {
      ...statusChipStyle({
        background: "rgba(36, 43, 52, 0.72)",
        border: "1px solid #4a5562",
        color: "#cfd9e2",
      }),
      opacity: 0.92,
    };

    return (
      <div
        className="rounded-md px-2.5 py-1.5 text-sm"
        style={placeholderStyle}
      >
        Loading objective status
      </div>
    );
  }

  return (
    <>
      {progressChips.map((chip, index) => {
        const complete = chip.status === "complete";
        const tone = objectiveTone(complete);
        return (
          <div
            key={chip.objective_key}
            className="rounded-md px-2.5 py-1.5 text-sm"
            style={{
              ...statusChipStyle(tone),
              animation: "progressChipIn 220ms ease-out both",
              animationDelay: `${index * 40}ms`,
            }}
          >
            {chip.label} {complete ? <strong>✓</strong> : null}
          </div>
        );
      })}
    </>
  );
}

export function SessionStatusHeader({
  agentStatus,
  completionStatus,
  completedAt,
  completionReasonCode,
  unreadFeedbackCount,
  feedbackItems,
  feedbackPanelOpen,
  onFeedbackChipClick,
  hasUnreadHint,
  unlockedHints,
  hintsReady,
  sessionState,
  hintsPanelOpen,
  onHintsChipClick,
  canStopSession,
  stoppingSession,
  onStopSession,
}: SessionStatusHeaderProps) {
  const agentTone = agentStatusTone(agentStatus);
  const hintsTone = hintTone(hasUnreadHint, unlockedHints.length > 0);
  const hasUnreadFeedback = unreadFeedbackCount > 0;
  const feedbackCount = feedbackItems.length;
  const feedbackTone = hintTone(hasUnreadFeedback, feedbackItems.length > 0);
  const tone = statusTone(sessionState);
  const normalizedAgentStatus = agentStatus.trim().toLowerCase();
  const agentLabel =
    normalizedAgentStatus === "active" ? "Agent: active" : "Agent: idle";
  const normalizedSessionState = sessionState.trim().toLowerCase();
  const sessionLabel =
    normalizedSessionState === "active"
      ? "Session: active"
      : "Session: provisioning";

  const renderHintsPopover = () => {
    if (!hintsPanelOpen) return null;

    return (
      <section
        className="hints-scroll-region absolute right-0 z-[4] box-border max-h-[640px] w-[420px] max-w-full overflow-x-hidden overflow-y-auto rounded-[10px] border border-sky-800 bg-slate-950 p-3 pr-1.5 shadow-[0_10px_24px_rgba(0,0,0,0.35)]"
        style={{
          position: "absolute",
          top: "calc(100% + 8px)",
          right: 0,
          zIndex: 4,
          width: 420,
          maxWidth: "100%",
          maxHeight: 640,
          overflowY: "auto",
          overflowX: "hidden",
          paddingRight: 6,
          boxSizing: "border-box",
        }}
      >
        {!hintsReady ? (
          <p className="m-0 opacity-90" />
        ) : unlockedHints.length === 0 ? (
          <p className="m-0 opacity-90">
            No hints unlocked yet. Continue interacting and check back.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {unlockedHints.map((hint) => (
              <div
                key={`hint-${hint.index}`}
                className="rounded-lg border border-fuchsia-700 bg-fuchsia-950/65 p-2.5"
              >
                <p className="mb-1 mt-0 font-bold text-fuchsia-100">
                  Hint {hint.index + 1}
                </p>
                <p className="mb-1.5 mt-0 text-fuchsia-50">{hint.text}</p>
                <p className="m-0 text-xs text-fuchsia-200">
                  Unlocked at {formatTime(hint.unlockedAt)}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>
    );
  };

  return (
    <>
      <button
        type="button"
        onClick={onFeedbackChipClick}
        className="rounded-md px-2.5 py-1.5 text-sm"
        style={{
          ...statusChipStyle(feedbackTone),
          cursor: "pointer",
          boxShadow: hasUnreadFeedback
            ? "0 0 0 1px rgba(255, 230, 166, 0.2), 0 0 12px rgba(255, 230, 166, 0.24)"
            : undefined,
        }}
      >
        <strong>Feedback</strong>
        {feedbackCount > 0 ? (
          <span className="ml-1.5">({feedbackCount})</span>
        ) : null}
      </button>
      <button
        type="button"
        onClick={onHintsChipClick}
        className="rounded-md px-2.5 py-1.5 text-sm"
        style={{
          ...statusChipStyle(hintsTone),
          cursor: "pointer",
          boxShadow: hasUnreadHint
            ? "0 0 0 1px rgba(255, 230, 166, 0.2), 0 0 12px rgba(255, 230, 166, 0.24)"
            : undefined,
        }}
      >
        <strong>Hints</strong>
        {unlockedHints.length > 0 ? (
          <span className="ml-1.5">({unlockedHints.length})</span>
        ) : null}
      </button>
      <div
        className="rounded-md px-2.5 py-1.5 text-sm"
        style={statusChipStyle(agentTone)}
      >
        <strong>{agentLabel}</strong>
      </div>
      <div
        className="rounded-md px-2.5 py-1.5 text-sm"
        style={statusChipStyle(tone)}
      >
        <strong>{sessionLabel}</strong>
      </div>
      {completionStatus === "completed_failure" ? (
        <SessionCompletionIndicator
          completionStatus={completionStatus}
          completedAt={completedAt}
          completionReasonCode={completionReasonCode}
        />
      ) : null}
      <button
        type="button"
        onClick={onStopSession}
        disabled={!canStopSession || stoppingSession}
        className="rounded-md px-2.5 py-1.5 text-sm"
        style={{
          ...statusChipStyle({
            background: "rgba(83, 21, 31, 0.72)",
            border: "1px solid #9b3e50",
            color: "#ffd7df",
          }),
          cursor:
            !canStopSession || stoppingSession ? "not-allowed" : "pointer",
          opacity: !canStopSession || stoppingSession ? 0.6 : 1,
        }}
      >
        <strong>{stoppingSession ? "Stopping..." : "Stop Session"}</strong>
      </button>
      {feedbackPanelOpen ? (
        <FeedbackPopover feedbackItems={feedbackItems} />
      ) : null}
      {renderHintsPopover()}
    </>
  );
}

export function SessionHeaderStatus(props: SessionHeaderStatusProps) {
  const {
    progressReady,
    progressChips,
    agentStatus,
    completionStatus,
    completedAt,
    completionReasonCode,
    unreadFeedbackCount,
    feedbackItems,
    feedbackPanelOpen,
    onFeedbackChipClick,
    hasUnreadHint,
    unlockedHints,
    hintsReady,
    sessionState,
    hintsPanelOpen,
    onHintsChipClick,
    canStopSession,
    stoppingSession,
    onStopSession,
  } = props;

  return (
    <div className="flex w-full flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap gap-2">
        <ProgressStatusHeader
          progressReady={progressReady}
          progressChips={progressChips}
        />
      </div>
      <div className="relative flex flex-wrap gap-2">
        <SessionStatusHeader
          agentStatus={agentStatus}
          completionStatus={completionStatus}
          completedAt={completedAt}
          completionReasonCode={completionReasonCode}
          unreadFeedbackCount={unreadFeedbackCount}
          feedbackItems={feedbackItems}
          feedbackPanelOpen={feedbackPanelOpen}
          onFeedbackChipClick={onFeedbackChipClick}
          hasUnreadHint={hasUnreadHint}
          unlockedHints={unlockedHints}
          hintsReady={hintsReady}
          sessionState={sessionState}
          hintsPanelOpen={hintsPanelOpen}
          onHintsChipClick={onHintsChipClick}
          canStopSession={canStopSession}
          stoppingSession={stoppingSession}
          onStopSession={onStopSession}
        />
      </div>
      <style>{`
        @keyframes progressChipIn {
          from { opacity: 0; transform: translateY(-3px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .hints-scroll-region {
          scrollbar-width: thin;
          scrollbar-color: #88a2b8 transparent;
        }
        .hints-scroll-region::-webkit-scrollbar {
          width: 10px;
        }
        .hints-scroll-region::-webkit-scrollbar-track {
          background: transparent;
        }
        .hints-scroll-region::-webkit-scrollbar-thumb {
          background-color: #88a2b8;
          border-radius: 999px;
          border: 2px solid transparent;
          background-clip: content-box;
        }
        .hints-scroll-region::-webkit-scrollbar-thumb:hover {
          background-color: #6f8ea8;
        }
      `}</style>
    </div>
  );
}
