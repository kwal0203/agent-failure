import { useEffect, useMemo, useRef, useState } from "react";
import type { TimelineEvent } from "../types";
import { DEMO_H2_STYLE } from "../ui";

type FeedbackColumnProps = {
  feedbackLoading: boolean;
  feedbackReady: boolean;
  feedbackError: string | null;
  timelineEvents: TimelineEvent[];
};

function isTokenExposureEvent(event: TimelineEvent): boolean {
  const haystack =
    `${event.title} ${event.description} ${event.details ?? ""}`.toLowerCase();
  return (
    haystack.includes("token exposed") ||
    haystack.includes("system_token") ||
    haystack.includes("orch-7429")
  );
}

function isMaliciousEmailReceivedEvent(event: TimelineEvent): boolean {
  return event.title.toLowerCase() === "malicious email received";
}

function isBenignEmailReceivedEvent(event: TimelineEvent): boolean {
  return event.title.toLowerCase() === "benign email received";
}

function eventTone(event: TimelineEvent): {
  border: string;
  background: string;
  titleColor: string;
  bodyColor: string;
} {
  if (isTokenExposureEvent(event)) {
    return {
      border: "1px solid #d14c4c",
      background: "rgba(93, 21, 21, 0.35)",
      titleColor: "#ffd7d7",
      bodyColor: "#ffe9e9",
    };
  }

  if (isMaliciousEmailReceivedEvent(event)) {
    return {
      border: "1px solid #cf513f",
      background: "rgba(98, 31, 22, 0.36)",
      titleColor: "#ffe0da",
      bodyColor: "#ffece7",
    };
  }

  if (isBenignEmailReceivedEvent(event)) {
    return {
      border: "1px solid #4e9d74",
      background: "rgba(25, 75, 52, 0.34)",
      titleColor: "#dbffe9",
      bodyColor: "#ebfff3",
    };
  }

  switch (event.type) {
    case "important":
      return {
        border: "1px solid #d18a3e",
        background: "rgba(94, 60, 20, 0.3)",
        titleColor: "#ffe4c0",
        bodyColor: "#ffefda",
      };
    case "attacker_action":
      return {
        border: "1px solid #8a4fd1",
        background: "rgba(63, 32, 96, 0.28)",
        titleColor: "#eadbff",
        bodyColor: "#f2e9ff",
      };
    case "agent_action":
      return {
        border: "1px solid #3e9a72",
        background: "rgba(24, 70, 52, 0.3)",
        titleColor: "#d8ffe8",
        bodyColor: "#e9fff2",
      };
    case "tool_call":
      return {
        border: "1px solid #3a8ec2",
        background: "rgba(22, 56, 82, 0.3)",
        titleColor: "#d6efff",
        bodyColor: "#e8f6ff",
      };
    case "system":
      return {
        border: "1px solid #8a95a1",
        background: "rgba(41, 49, 56, 0.3)",
        titleColor: "#e5ebf2",
        bodyColor: "#f1f5f9",
      };
    case "explanation":
      return {
        border: "1px solid #4a86c6",
        background: "rgba(20, 50, 78, 0.3)",
        titleColor: "#d6ecff",
        bodyColor: "#e9f4ff",
      };
    default:
      return {
        border: "1px solid #8ea1b4",
        background: "rgba(26, 38, 49, 0.18)",
        titleColor: "#e6edf3",
        bodyColor: "#f2f5f7",
      };
  }
}

export function FeedbackColumn({
  feedbackLoading,
  feedbackReady,
  feedbackError,
  timelineEvents,
}: FeedbackColumnProps) {
  const [selectedEventIds, setSelectedEventIds] = useState<Set<string>>(
    () => new Set(),
  );
  const controlsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onPointerDown = (event: MouseEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (controlsRef.current?.contains(target)) return;
    };

    window.addEventListener("mousedown", onPointerDown);
    return () => {
      window.removeEventListener("mousedown", onPointerDown);
    };
  }, []);

  const sortedEvents = useMemo(
    () =>
      [...timelineEvents].sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      ),
    [timelineEvents],
  );

  useEffect(() => {
    const knownIds = new Set(sortedEvents.map((event) => event.id));
    setSelectedEventIds((prev) => {
      const next = new Set<string>();
      for (const id of prev) {
        if (knownIds.has(id)) {
          next.add(id);
        }
      }
      return next;
    });
  }, [sortedEvents]);

  const selectedCount = selectedEventIds.size;

  const toggleEventSelection = (eventId: string) => {
    setSelectedEventIds((prev) => {
      const next = new Set(prev);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
  };

  return (
    <section
      style={{
        borderBottom: "2px solid #8ea5b8",
        borderRadius: 0,
        padding: 16,
        textAlign: "left",
        display: "flex",
        flexDirection: "column",
        flex: "1 1 0%",
        gap: 10,
        height: "100%",
        minHeight: 0,
        maxHeight: "100%",
        boxSizing: "border-box",
        overflow: "hidden",
      }}
    >
      <div style={{ flex: "0 0 auto" }}>
        <h2 style={{ ...DEMO_H2_STYLE, textAlign: "right" }}>Event Timeline</h2>
        {feedbackLoading ? (
          <p style={{ margin: "8px 0 0 0" }}>Loading learner feedback...</p>
        ) : null}
        {feedbackError ? (
          <p style={{ color: "red", margin: "8px 0 0 0" }}>
            Error: {feedbackError}
          </p>
        ) : null}
      </div>

      <div
        className="timeline-scroll-region"
        style={{
          flex: "1 1 auto",
          height: 0,
          minHeight: 0,
          overflowY: "auto",
          paddingRight: 6,
          scrollbarGutter: "stable",
        }}
      >
        {!feedbackReady ? (
          <p style={{ margin: 0, opacity: 0.85 }} />
        ) : sortedEvents.length === 0 ? (
          <p style={{ margin: 0, opacity: 0.85 }}>No events to display.</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {sortedEvents.map((event, index) => {
              const tone = eventTone(event);
              const isSelected = selectedEventIds.has(event.id);
              const isSelectable = event.report_selectable === true;
              const chipStyle = {
                border: tone.border,
                background: tone.background,
                borderRadius: 8,
                padding: 10,
                opacity: 0,
                transform: "translateY(4px)",
                animationName: "timelineEventIn",
                animationDuration: "330ms",
                animationTimingFunction: "ease-out",
                animationFillMode: "forwards",
                animationDelay: `${Math.min(index, 8) * 36}ms`,
                boxShadow: isSelected
                  ? "0 0 0 1px rgba(255, 255, 255, 0.12)"
                  : undefined,
                filter: isSelected ? "brightness(1.08)" : undefined,
                cursor: isSelectable ? "pointer" : "default",
              } as const;
              const chipBody = (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: 0,
                    alignItems: "flex-start",
                    position: "relative",
                  }}
                >
                  {isSelected ? (
                    <span
                      aria-hidden="true"
                      style={{
                        position: "absolute",
                        top: -4,
                        right: -2,
                        width: 16,
                        height: 16,
                        borderRadius: "999px",
                        background: "rgba(210, 235, 255, 0.95)",
                        color: "#1f5f85",
                        fontSize: 11,
                        lineHeight: "16px",
                        textAlign: "center",
                        fontWeight: 700,
                        boxShadow: "0 0 0 1px rgba(17, 24, 39, 0.35)",
                      }}
                    >
                      ✓
                    </span>
                  ) : null}
                  <p
                    style={{
                      margin: 0,
                      fontWeight: 600,
                      color: tone.titleColor,
                    }}
                  >
                    {event.title}
                  </p>
                </div>
              );

              if (isSelectable) {
                return (
                  <button
                    key={event.id}
                    type="button"
                    aria-pressed={isSelected}
                    onClick={() => {
                      toggleEventSelection(event.id);
                    }}
                    style={{
                      ...chipStyle,
                      borderWidth: 1,
                      borderStyle: "solid",
                      textAlign: "left",
                      width: "100%",
                    }}
                  >
                    {chipBody}
                  </button>
                );
              }

              return (
                <div key={event.id} style={chipStyle}>
                  {chipBody}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <style>{`
        @keyframes timelineEventIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .timeline-scroll-region {
          scrollbar-width: thin;
          scrollbar-color: #88a2b8 transparent;
        }
        .timeline-scroll-region::-webkit-scrollbar {
          width: 10px;
        }
        .timeline-scroll-region::-webkit-scrollbar-track {
          background: transparent;
        }
        .timeline-scroll-region::-webkit-scrollbar-thumb {
          background-color: #88a2b8;
          border-radius: 999px;
          border: 2px solid transparent;
          background-clip: content-box;
        }
        .timeline-scroll-region::-webkit-scrollbar-thumb:hover {
          background-color: #6f8ea8;
        }
      `}</style>

      <div
        ref={controlsRef}
        style={{
          flex: "0 0 auto",
          display: "flex",
          gap: 12,
          alignItems: "center",
          flexWrap: "wrap",
          position: "relative",
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 13, color: "#d6f1ff" }}>
          Selected: {selectedCount}
        </span>
      </div>
    </section>
  );
}
