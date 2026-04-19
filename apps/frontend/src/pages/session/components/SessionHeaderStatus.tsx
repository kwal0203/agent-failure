import {
  agentStatusTone,
  formatTime,
  hintTone,
  objectiveTone,
  statusChipStyle,
} from "../helpers";
import type { AgentStatus, UnlockedHint } from "../types";
import { statusTone } from "../ui";

type ProgressStatusHeaderProps = {
  progressReady: boolean;
  inboxComplete: boolean;
  contextComplete: boolean;
  tokenComplete: boolean;
};

type SessionStatusHeaderProps = {
  agentStatus: AgentStatus;
  hasUnreadHint: boolean;
  unlockedHints: UnlockedHint[];
  sessionState: string;
  hintsPanelOpen: boolean;
  onHintsChipClick: () => void;
};

type SessionHeaderStatusProps = {
  progressReady: boolean;
  inboxComplete: boolean;
  contextComplete: boolean;
  tokenComplete: boolean;
  agentStatus: AgentStatus;
  hasUnreadHint: boolean;
  unlockedHints: UnlockedHint[];
  sessionState: string;
  hintsPanelOpen: boolean;
  onHintsChipClick: () => void;
};

export function ProgressStatusHeader({
  progressReady,
  inboxComplete,
  contextComplete,
  tokenComplete,
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
      <>
        <div style={placeholderStyle}>Malicious email injected</div>
        <div style={placeholderStyle}>
          Malicious instructions entered context
        </div>
        <div style={placeholderStyle}>Token exposed</div>
      </>
    );
  }

  const inboxTone = objectiveTone(inboxComplete);
  const contextTone = objectiveTone(contextComplete);
  const tokenTone = objectiveTone(tokenComplete);

  return (
    <>
      <div
        style={{
          ...statusChipStyle(inboxTone),
          animation: "progressChipIn 220ms ease-out both",
          animationDelay: "0ms",
        }}
      >
        Malicious email injected {inboxComplete ? <strong>✓</strong> : null}
      </div>
      <div
        style={{
          ...statusChipStyle(contextTone),
          animation: "progressChipIn 220ms ease-out both",
          animationDelay: "40ms",
        }}
      >
        Malicious instructions entered context{" "}
        {contextComplete ? <strong>✓</strong> : null}
      </div>
      <div
        style={{
          ...statusChipStyle(tokenTone),
          animation: "progressChipIn 220ms ease-out both",
          animationDelay: "80ms",
        }}
      >
        Token exposed {tokenComplete ? <strong>✓</strong> : null}
      </div>
    </>
  );
}

export function SessionStatusHeader({
  agentStatus,
  hasUnreadHint,
  unlockedHints,
  sessionState,
  hintsPanelOpen,
  onHintsChipClick,
}: SessionStatusHeaderProps) {
  const agentTone = agentStatusTone(agentStatus);
  const hintsTone = hintTone(hasUnreadHint, unlockedHints.length > 0);
  const tone = statusTone(sessionState);

  const renderHintsPopover = () => {
    if (!hintsPanelOpen) return null;

    return (
      <section
        style={{
          position: "absolute",
          top: "calc(100% + 8px)",
          right: 0,
          zIndex: 4,
          width: 420,
          maxWidth: "100%",
          background: "rgba(9, 19, 31, 0.95)",
          border: "1px solid #285272",
          borderRadius: 10,
          padding: 12,
          boxSizing: "border-box",
        }}
      >
        <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>Hints</h3>
        {unlockedHints.length === 0 ? (
          <p style={{ margin: 0, opacity: 0.88 }}>
            No hints unlocked yet. Continue interacting and check back.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {unlockedHints.map((hint) => (
              <div
                key={`hint-${hint.index}`}
                style={{
                  border: "1px solid #35607f",
                  borderRadius: 8,
                  padding: 10,
                  background: "rgba(11, 34, 54, 0.62)",
                }}
              >
                <p style={{ margin: "0 0 4px", fontWeight: 700 }}>
                  Hint {hint.index + 1}
                </p>
                <p style={{ margin: "0 0 6px" }}>{hint.text}</p>
                <p style={{ margin: 0, fontSize: 12, opacity: 0.82 }}>
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
      <div style={statusChipStyle(agentTone)}>
        <strong>Agent</strong>
      </div>
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
      <div style={statusChipStyle(tone)}>
        <strong>SESSION</strong>
      </div>
      {renderHintsPopover()}
    </>
  );
}

export function SessionHeaderStatus(props: SessionHeaderStatusProps) {
  const {
    progressReady,
    inboxComplete,
    contextComplete,
    tokenComplete,
    agentStatus,
    hasUnreadHint,
    unlockedHints,
    sessionState,
    hintsPanelOpen,
    onHintsChipClick,
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
          inboxComplete={inboxComplete}
          contextComplete={contextComplete}
          tokenComplete={tokenComplete}
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
          hasUnreadHint={hasUnreadHint}
          unlockedHints={unlockedHints}
          sessionState={sessionState}
          hintsPanelOpen={hintsPanelOpen}
          onHintsChipClick={onHintsChipClick}
        />
      </div>
      <style>{`
        @keyframes progressChipIn {
          from { opacity: 0; transform: translateY(-3px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
