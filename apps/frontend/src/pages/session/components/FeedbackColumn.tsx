import { useEffect, useMemo, useRef, useState } from "react";
import type {
  GetSessionReportEvidenceResponse,
  PutSessionReportEvidenceRequest,
  TimelineEvent,
} from "../types";
import { API_BASE, getAuthHeader } from "../ui";

type FeedbackColumnProps = {
  sessionId?: string;
  feedbackLoading: boolean;
  feedbackReady: boolean;
  feedbackError: string | null;
  timelineEvents: TimelineEvent[];
};

function toTraceEventId(timelineEventId: string): string | null {
  if (!timelineEventId.startsWith("trace-")) return null;
  const raw = timelineEventId.slice("trace-".length).trim();
  return raw.length > 0 ? raw : null;
}

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
  sessionId,
  feedbackLoading,
  feedbackReady,
  feedbackError,
  timelineEvents,
}: FeedbackColumnProps) {
  const [selectedEventIds, setSelectedEventIds] = useState<Set<string>>(
    () => new Set(),
  );
  const controlsRef = useRef<HTMLDivElement | null>(null);
  const [hasHydratedSelection, setHasHydratedSelection] = useState(false);
  const [preselectedTraceEventIds, setPreselectedTraceEventIds] = useState<
    Set<string>
  >(() => new Set());
  const preselectionAppliedRef = useRef(false);
  const sortedEvents = useMemo(
    () =>
      [...timelineEvents].sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      ),
    [timelineEvents],
  );

  useEffect(() => {
    void sessionId;
    setSelectedEventIds(new Set());
    setPreselectedTraceEventIds(new Set());
    setHasHydratedSelection(false);
    preselectionAppliedRef.current = false;
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) {
      setHasHydratedSelection(true);
      return;
    }

    let cancelled = false;
    const loadSelection = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/api/v1/sessions/${sessionId}/report-evidence`,
          {
            method: "GET",
            headers: {
              Authorization: getAuthHeader(),
              "Content-Type": "application/json",
            },
          },
        );
        if (!response.ok) {
          return;
        }
        const data =
          (await response.json()) as GetSessionReportEvidenceResponse;
        const items = Array.isArray(data.items) ? data.items : [];
        if (cancelled) return;
        setPreselectedTraceEventIds(
          new Set(
            items
              .map((item) => item.event_id)
              .filter((eventId): eventId is string => !!eventId),
          ),
        );
        preselectionAppliedRef.current = false;
      } finally {
        if (!cancelled) {
          setHasHydratedSelection(true);
        }
      }
    };
    void loadSelection();

    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    if (!hasHydratedSelection) return;
    if (preselectionAppliedRef.current) return;
    if (sortedEvents.length === 0) return;

    const selectedFromServer = new Set<string>();
    for (const event of sortedEvents) {
      if (event.report_selectable !== true) continue;
      const traceEventId = toTraceEventId(event.id);
      if (!traceEventId) continue;
      if (preselectedTraceEventIds.has(traceEventId)) {
        selectedFromServer.add(event.id);
      }
    }
    setSelectedEventIds(selectedFromServer);
    preselectionAppliedRef.current = true;
  }, [hasHydratedSelection, preselectedTraceEventIds, sortedEvents]);

  useEffect(() => {
    if (!sessionId) return;
    if (!hasHydratedSelection) return;

    const timeoutId = window.setTimeout(() => {
      const selectedItems = sortedEvents.filter(
        (event) =>
          event.report_selectable === true && selectedEventIds.has(event.id),
      );
      const requestBody: PutSessionReportEvidenceRequest = {
        items: selectedItems
          .map((event, index) => {
            const eventId = toTraceEventId(event.id);
            if (!eventId) return null;
            return {
              event_id: eventId,
              position: index,
              title: event.title,
              description: event.description,
              details: null,
              occurred_at: event.timestamp,
              trace_version: 1,
              event_index: index,
              evidence_type: event.evidence_type ?? "noise",
              objective_keys: event.objective_keys ?? [],
              why_it_matters: event.why_it_matters ?? null,
              default_priority: event.default_priority ?? "low",
              citation_label: null,
              objective_mapping: null,
              evidence_strength: null,
              student_note: null,
            };
          })
          .filter((item) => item !== null),
      };

      void fetch(`${API_BASE}/api/v1/sessions/${sessionId}/report-evidence`, {
        method: "PUT",
        headers: {
          Authorization: getAuthHeader(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });
    }, 450);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [hasHydratedSelection, selectedEventIds, sessionId, sortedEvents]);

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
              const isSelected = selectedEventIds.has(event.id);
              const isSelectable = event.report_selectable === true;
              const chipStyle = {
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
              } as const;
              const chipBody = (
                <div className="relative flex flex-col items-start gap-0">
                  {isSelected ? (
                    <span
                      aria-hidden="true"
                      className="absolute -right-0.5 -top-1 h-4 w-4 rounded-full bg-sky-100 text-center text-[11px] font-bold leading-4 text-sky-800 shadow-[0_0_0_1px_rgba(17,24,39,0.35)]"
                    >
                      ✓
                    </span>
                  ) : null}
                  <p className={`m-0 font-semibold ${tone.titleClass}`}>
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
                    style={chipStyle}
                    className={`w-full cursor-pointer rounded-lg px-2.5 py-2.5 text-left ${tone.chipClass}`}
                  >
                    {chipBody}
                  </button>
                );
              }

              return (
                <div
                  key={event.id}
                  style={chipStyle}
                  className={`w-full cursor-default rounded-lg px-2.5 py-2.5 ${tone.chipClass}`}
                >
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

      <div
        ref={controlsRef}
        className="relative flex flex-none flex-wrap items-center gap-3"
      >
        <span className="text-sm font-semibold text-sky-100">
          Selected: {selectedCount}
        </span>
      </div>
    </section>
  );
}
