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
  SessionProgressChip,
  UnlockedHint,
} from "../types";
import { statusTone } from "../ui";
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

    return <div style={placeholderStyle}>Loading objective status</div>;
  }

  return (
    <>
      {progressChips.map((chip, index) => {
        const complete = chip.status === "complete";
        const tone = objectiveTone(complete);
        return (
          <div
            key={chip.objective_key}
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
        className="hints-scroll-region"
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
          background: "#09131f",
          border: "1px solid #35607f",
          borderRadius: 10,
          padding: 12,
          boxSizing: "border-box",
          boxShadow: "0 10px 24px rgba(0, 0, 0, 0.35)",
        }}
      >
        {!hintsReady ? (
          <p style={{ margin: 0, opacity: 0.88 }} />
        ) : unlockedHints.length === 0 ? (
          <p style={{ margin: 0, opacity: 0.88 }}>
            No hints unlocked yet. Continue interacting and check back.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {unlockedHints.map((hint) => (
              <div
                key={`hint-${hint.index}`}
                style={{
                  border: "1px solid #9a4f8a",
                  borderRadius: 8,
                  padding: 10,
                  background: "rgba(64, 24, 58, 0.64)",
                }}
              >
                <p
                  style={{
                    margin: "0 0 4px",
                    fontWeight: 700,
                    color: "#ffd8f5",
                  }}
                >
                  Hint {hint.index + 1}
                </p>
                <p style={{ margin: "0 0 6px", color: "#ffeafd" }}>
                  {hint.text}
                </p>
                <p style={{ margin: 0, fontSize: 12, color: "#f2cbe8" }}>
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
        onClick={onHintsChipClick}
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
          <span style={{ marginLeft: 6 }}>({unlockedHints.length})</span>
        ) : null}
      </button>
      <div style={statusChipStyle(agentTone)}>
        <strong>{agentLabel}</strong>
      </div>
      <div style={statusChipStyle(tone)}>
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
    <div
      style={{
        width: "100%",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
        flexWrap: "wrap",
      }}
    >
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <ProgressStatusHeader
          progressReady={progressReady}
          progressChips={progressChips}
        />
      </div>
      <div
        style={{
          display: "flex",
          gap: 8,
          flexWrap: "wrap",
          position: "relative",
        }}
      >
        <SessionStatusHeader
          agentStatus={agentStatus}
          completionStatus={completionStatus}
          completedAt={completedAt}
          completionReasonCode={completionReasonCode}
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
