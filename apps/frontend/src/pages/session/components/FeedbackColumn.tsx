import { useMemo } from "react";
import type { TimelineEvent } from "../types";

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
  chipClass: string;
  titleClass: string;
} {
  if (isTokenExposureEvent(event)) {
    return {
      chipClass: "border border-red-500 bg-red-950/35",
      titleClass: "text-red-100",
    };
  }

  if (isMaliciousEmailReceivedEvent(event)) {
    return {
      chipClass: "border border-orange-500 bg-orange-950/35",
      titleClass: "text-orange-100",
    };
  }

  if (isBenignEmailReceivedEvent(event)) {
    return {
      chipClass: "border border-emerald-500 bg-emerald-950/35",
      titleClass: "text-emerald-100",
    };
  }

  switch (event.type) {
    case "important":
      return {
        chipClass: "border border-amber-500 bg-amber-950/30",
        titleClass: "text-amber-100",
      };
    case "attacker_action":
      return {
        chipClass: "border border-violet-500 bg-violet-950/30",
        titleClass: "text-violet-100",
      };
    case "agent_action":
      return {
        chipClass: "border border-emerald-500 bg-emerald-950/30",
        titleClass: "text-emerald-100",
      };
    case "tool_call":
      return {
        chipClass: "border border-sky-500 bg-sky-950/30",
        titleClass: "text-sky-100",
      };
    case "system":
      return {
        chipClass: "border border-slate-500 bg-slate-800/45",
        titleClass: "text-slate-100",
      };
    case "explanation":
      return {
        chipClass: "border border-blue-500 bg-blue-950/30",
        titleClass: "text-blue-100",
      };
    default:
      return {
        chipClass: "border border-slate-400 bg-slate-900/25",
        titleClass: "text-slate-100",
      };
  }
}

export function FeedbackColumn({
  feedbackLoading,
  feedbackReady,
  feedbackError,
  timelineEvents,
}: FeedbackColumnProps) {
  const sortedEvents = useMemo(
    () =>
      [...timelineEvents].sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      ),
    [timelineEvents],
  );

  return (
    <section className="box-border flex h-full min-h-0 max-h-full flex-[1_1_0%] flex-col gap-2.5 overflow-hidden border-b-2 border-slate-400 px-4 py-4 text-left">
      <div className="flex-none">
        <h2 className="m-0 text-right text-lg font-semibold tracking-wide text-slate-100">
          Event Timeline
        </h2>
        {feedbackLoading ? (
          <p className="mb-0 mt-2">Loading learner feedback...</p>
        ) : null}
        {feedbackError ? (
          <p className="mb-0 mt-2 text-red-400">Error: {feedbackError}</p>
        ) : null}
      </div>

      <div
        className="timeline-scroll-region"
        style={{ scrollbarGutter: "stable" }}
      >
        {!feedbackReady ? (
          <p className="m-0 opacity-85" />
        ) : sortedEvents.length === 0 ? (
          <p className="m-0 opacity-85">No events to display.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {sortedEvents.map((event, index) => {
              const tone = eventTone(event);
              const chipStyle = {
                opacity: 0,
                transform: "translateY(4px)",
                animationName: "timelineEventIn",
                animationDuration: "330ms",
                animationTimingFunction: "ease-out",
                animationFillMode: "forwards",
                animationDelay: `${Math.min(index, 8) * 36}ms`,
              } as const;
              return (
                <div
                  key={event.id}
                  style={chipStyle}
                  className={`w-full cursor-default rounded-lg px-2.5 py-2.5 ${tone.chipClass}`}
                >
                  <div className="flex flex-col items-start gap-0">
                    <p className={`m-0 font-semibold ${tone.titleClass}`}>
                      {event.title}
                    </p>
                  </div>
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
          flex: 1 1 auto;
          height: 0;
          min-height: 0;
          overflow-y: auto;
          padding-right: 6px;
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
    </section>
  );
}
