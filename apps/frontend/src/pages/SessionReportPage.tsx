import { ArrowLeft, Download, FileText, Save } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { mapPersistedTraceToTimelineEvent } from "./session/timelineEventMapper";
import type {
  GetSessionReportEvidenceResponse,
  GetSessionTraceResponse,
  PutSessionReportEvidenceRequest,
  TimelineEvent,
} from "./session/types";
import { API_BASE, getAuthHeader } from "./session/ui";

type DraftSections = {
  executiveSummary: string;
  threatModel: string;
  methodology: string;
  evidenceAndResults: string;
  mitigations: string;
};

const DEFAULT_DRAFT: DraftSections = {
  executiveSummary: "",
  threatModel: "",
  methodology: "",
  evidenceAndResults: "",
  mitigations: "",
};

type ReportSection =
  | "unassigned"
  | "executive_summary"
  | "threat_model"
  | "methodology"
  | "evidence_and_results"
  | "mitigations";

const REPORT_SECTION_OPTIONS: ReadonlyArray<{
  value: ReportSection;
  label: string;
}> = [
  { value: "unassigned", label: "Unassigned" },
  { value: "executive_summary", label: "Executive Summary" },
  { value: "threat_model", label: "Threat Model" },
  { value: "methodology", label: "Methodology" },
  { value: "evidence_and_results", label: "Evidence & Results" },
  { value: "mitigations", label: "Mitigations" },
];

export default function SessionReportPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [draft, setDraft] = useState<DraftSections>(DEFAULT_DRAFT);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [loadingEvidence, setLoadingEvidence] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedEventIds, setSelectedEventIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [selectedEventSections, setSelectedEventSections] = useState<
    Record<string, ReportSection>
  >({});
  const [hasHydratedSelection, setHasHydratedSelection] = useState(false);
  const [preselectedTraceEventIds, setPreselectedTraceEventIds] = useState<
    Set<string>
  >(() => new Set());
  const [
    preselectedSectionsByTraceEventId,
    setPreselectedSectionsByTraceEventId,
  ] = useState<Record<string, ReportSection>>({});

  const toTraceEventId = useCallback(
    (timelineEventId: string): string | null => {
      if (!timelineEventId.startsWith("trace-")) return null;
      const raw = timelineEventId.slice("trace-".length).trim();
      return raw.length > 0 ? raw : null;
    },
    [],
  );

  const isTokenExposureEvent = (event: TimelineEvent): boolean => {
    const haystack =
      `${event.title} ${event.description} ${event.details ?? ""}`.toLowerCase();
    return (
      haystack.includes("token exposed") ||
      haystack.includes("system_token") ||
      haystack.includes("orch-7429")
    );
  };

  const isMaliciousEmailReceivedEvent = (event: TimelineEvent): boolean => {
    return event.title.toLowerCase() === "malicious email received";
  };

  const isBenignEmailReceivedEvent = (event: TimelineEvent): boolean => {
    return event.title.toLowerCase() === "benign email received";
  };

  const eventTone = (
    event: TimelineEvent,
  ): {
    chipClass: string;
    titleClass: string;
  } => {
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
  };

  const refreshEvidence = useCallback(async () => {
    if (!sessionId) return;
    setLoadingEvidence(true);
    setError(null);
    try {
      const traceResponse = await fetch(
        `${API_BASE}/api/v1/sessions/${sessionId}/trace`,
        {
          method: "GET",
          headers: {
            Authorization: getAuthHeader(),
            "Content-Type": "application/json",
          },
        },
      );
      if (!traceResponse.ok) {
        throw new Error(
          `Failed to load session timeline (HTTP ${traceResponse.status})`,
        );
      }
      const tracePayload =
        (await traceResponse.json()) as GetSessionTraceResponse;
      const traceEvents = Array.isArray(tracePayload.events)
        ? tracePayload.events
        : [];
      const mappedTimelineEvents = traceEvents
        .map((event) => mapPersistedTraceToTimelineEvent(event))
        .filter((event): event is TimelineEvent => event !== null);
      setTimelineEvents(mappedTimelineEvents);

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
        throw new Error(`Failed to load evidence (HTTP ${response.status})`);
      }
      const payload =
        (await response.json()) as GetSessionReportEvidenceResponse;
      const items = Array.isArray(payload.items) ? payload.items : [];
      setPreselectedTraceEventIds(
        new Set(
          items
            .map((item) => item.event_id)
            .filter((eventId): eventId is string => !!eventId),
        ),
      );
      const sectionMap: Record<string, ReportSection> = {};
      for (const item of items) {
        if (!item?.event_id) continue;
        const section =
          item.report_section &&
          REPORT_SECTION_OPTIONS.some(
            (opt) => opt.value === item.report_section,
          )
            ? (item.report_section as ReportSection)
            : "unassigned";
        sectionMap[item.event_id] = section;
      }
      setPreselectedSectionsByTraceEventId(sectionMap);
      setHasHydratedSelection(true);
    } catch (fetchError) {
      setError(
        fetchError instanceof Error ? fetchError.message : "Unknown error",
      );
      setHasHydratedSelection(true);
    } finally {
      setLoadingEvidence(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void refreshEvidence();
  }, [refreshEvidence]);

  const orderedEvidence = useMemo(
    () =>
      [...timelineEvents].sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      ),
    [timelineEvents],
  );

  useEffect(() => {
    if (!hasHydratedSelection) return;
    if (orderedEvidence.length === 0) return;

    const selectedFromServer = new Set<string>();
    const sectionsByTimelineEventId: Record<string, ReportSection> = {};
    for (const event of orderedEvidence) {
      if (event.report_selectable !== true) continue;
      const traceEventId = toTraceEventId(event.id);
      if (!traceEventId) continue;
      if (preselectedTraceEventIds.has(traceEventId)) {
        selectedFromServer.add(event.id);
        sectionsByTimelineEventId[event.id] =
          preselectedSectionsByTraceEventId[traceEventId] ?? "unassigned";
      }
    }
    setSelectedEventIds(selectedFromServer);
    setSelectedEventSections(sectionsByTimelineEventId);
  }, [
    hasHydratedSelection,
    orderedEvidence,
    preselectedTraceEventIds,
    preselectedSectionsByTraceEventId,
    toTraceEventId,
  ]);

  useEffect(() => {
    if (!sessionId) return;
    if (!hasHydratedSelection) return;

    const timeoutId = window.setTimeout(() => {
      const selectedItems = orderedEvidence.filter(
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
              report_section: selectedEventSections[event.id] ?? "unassigned",
              section_position: null,
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
  }, [
    hasHydratedSelection,
    orderedEvidence,
    selectedEventSections,
    selectedEventIds,
    sessionId,
    toTraceEventId,
  ]);

  const toggleEventSelection = (eventId: string) => {
    const wasSelected = selectedEventIds.has(eventId);
    setSelectedEventIds((prev) => {
      const next = new Set(prev);
      if (wasSelected) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
    setSelectedEventSections((prevSections) => {
      const nextSections = { ...prevSections };
      if (wasSelected) {
        delete nextSections[eventId];
      } else if (!nextSections[eventId]) {
        nextSections[eventId] = "unassigned";
      }
      return nextSections;
    });
  };

  const setEventSection = (eventId: string, section: ReportSection) => {
    setSelectedEventSections((prev) => ({ ...prev, [eventId]: section }));
  };

  const selectedEvidenceBySection = useMemo(() => {
    const grouped = new Map<ReportSection, TimelineEvent[]>();
    for (const option of REPORT_SECTION_OPTIONS) {
      grouped.set(option.value, []);
    }
    for (const event of orderedEvidence) {
      if (!selectedEventIds.has(event.id)) continue;
      const section = selectedEventSections[event.id] ?? "unassigned";
      const bucket = grouped.get(section);
      if (bucket) {
        bucket.push(event);
      }
    }
    return grouped;
  }, [orderedEvidence, selectedEventIds, selectedEventSections]);

  const updateDraftField = <K extends keyof DraftSections>(
    key: K,
    value: DraftSections[K],
  ) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="min-h-full bg-black font-sans text-slate-100">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-5 py-6 md:px-8 lg:px-10">
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => navigate("/reports")}
            className="inline-flex items-center gap-2 rounded-lg border border-lime-500/35 bg-black/40 px-3 py-2 text-xs font-bold uppercase tracking-wide text-lime-200 transition hover:bg-lime-500/10"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Reports
          </button>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled
              className="inline-flex items-center gap-2 rounded-lg border border-slate-500/40 bg-slate-900/50 px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-300 opacity-60"
              title="Save will be added in the next step."
            >
              <Save className="h-4 w-4" />
              Save
            </button>
            <button
              type="button"
              disabled
              className="inline-flex items-center gap-2 rounded-lg border border-slate-500/40 bg-slate-900/50 px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-300 opacity-60"
              title="Export will be added in the next step."
            >
              <Download className="h-4 w-4" />
              Export
            </button>
          </div>
        </div>

        <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="rounded-2xl border border-lime-500/20 bg-slate-950/65 p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="rounded-lg border border-lime-400/35 bg-lime-500/10 p-1.5 text-lime-200">
                  <FileText className="h-4 w-4" />
                </div>
                <h2 className="m-0 text-sm font-black uppercase tracking-wide text-lime-300">
                  Evidence
                </h2>
              </div>
              <div />
            </div>
            {error ? (
              <p className="mb-3 rounded-lg border border-rose-500/45 bg-rose-950/25 px-3 py-2 text-sm text-rose-200">
                {error}
              </p>
            ) : null}
            <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
              {loadingEvidence ? (
                <p className="text-sm text-slate-400">Loading evidence...</p>
              ) : orderedEvidence.length === 0 ? (
                <p className="text-sm text-slate-400">
                  No evidence found for this session in database.
                </p>
              ) : (
                orderedEvidence.map((event) => {
                  const isSelected = selectedEventIds.has(event.id);
                  const isSelectable = event.report_selectable === true;
                  const tone = eventTone(event);
                  const selectedSection =
                    selectedEventSections[event.id] ?? "unassigned";
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
                      {isSelected ? (
                        <label className="mt-2 inline-flex items-center gap-2 rounded-full border border-slate-500/35 bg-black/40 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-200">
                          Section
                          <select
                            value={selectedSection}
                            onChange={(selectEvent) => {
                              setEventSection(
                                event.id,
                                selectEvent.target.value as ReportSection,
                              );
                            }}
                            onClick={(selectEvent) =>
                              selectEvent.stopPropagation()
                            }
                            className="rounded-full border border-slate-500/40 bg-slate-900/90 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-slate-100 outline-none"
                          >
                            {REPORT_SECTION_OPTIONS.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </label>
                      ) : null}
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
                        className={`w-full cursor-pointer rounded-lg px-2.5 py-2.5 text-left ${tone.chipClass}`}
                        style={{
                          boxShadow: isSelected
                            ? "0 0 0 1px rgba(255, 255, 255, 0.12)"
                            : undefined,
                          filter: isSelected ? "brightness(1.08)" : undefined,
                        }}
                      >
                        {chipBody}
                      </button>
                    );
                  }

                  return (
                    <div
                      key={event.id}
                      className={`w-full cursor-default rounded-lg px-2.5 py-2.5 ${tone.chipClass}`}
                    >
                      {chipBody}
                    </div>
                  );
                })
              )}
            </div>
          </aside>

          <section className="space-y-4 rounded-2xl border border-lime-500/20 bg-slate-950/65 p-4">
            <h2 className="m-0 text-sm font-black uppercase tracking-wide text-lime-300">
              Report Draft
            </h2>

            <div className="rounded-xl border border-slate-600/30 bg-black/25 p-3">
              <p className="mb-3 text-xs font-black uppercase tracking-wide text-slate-300">
                Evidence By Section
              </p>
              <div className="grid gap-3 md:grid-cols-2">
                {REPORT_SECTION_OPTIONS.map((sectionOption) => {
                  const eventsForSection =
                    selectedEvidenceBySection.get(sectionOption.value) ?? [];
                  return (
                    <div
                      key={sectionOption.value}
                      className="rounded-lg border border-slate-600/35 bg-slate-900/35 p-2.5"
                    >
                      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-300">
                        {sectionOption.label}
                      </p>
                      {eventsForSection.length === 0 ? (
                        <p className="text-xs text-slate-500">
                          No evidence assigned
                        </p>
                      ) : (
                        <div className="space-y-1">
                          {eventsForSection.map((event) => (
                            <div
                              key={event.id}
                              className="rounded border border-slate-500/30 bg-black/35 px-2 py-1 text-xs text-slate-200"
                            >
                              {event.title}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            <label className="grid gap-2">
              <span className="text-sm font-bold text-slate-200">
                Executive Summary
              </span>
              <textarea
                value={draft.executiveSummary}
                onChange={(event) =>
                  updateDraftField("executiveSummary", event.target.value)
                }
                rows={5}
                className="w-full rounded-xl border border-lime-500/25 bg-black/35 px-3 py-2 text-sm leading-6 text-slate-100 outline-none transition focus:border-lime-400"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-sm font-bold text-slate-200">
                Threat Model
              </span>
              <textarea
                value={draft.threatModel}
                onChange={(event) =>
                  updateDraftField("threatModel", event.target.value)
                }
                rows={5}
                className="w-full rounded-xl border border-lime-500/25 bg-black/35 px-3 py-2 text-sm leading-6 text-slate-100 outline-none transition focus:border-lime-400"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-sm font-bold text-slate-200">
                Exploitation Methodology
              </span>
              <textarea
                value={draft.methodology}
                onChange={(event) =>
                  updateDraftField("methodology", event.target.value)
                }
                rows={6}
                className="w-full rounded-xl border border-lime-500/25 bg-black/35 px-3 py-2 text-sm leading-6 text-slate-100 outline-none transition focus:border-lime-400"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-sm font-bold text-slate-200">
                Evidence and Results
              </span>
              <textarea
                value={draft.evidenceAndResults}
                onChange={(event) =>
                  updateDraftField("evidenceAndResults", event.target.value)
                }
                rows={8}
                className="w-full rounded-xl border border-lime-500/25 bg-black/35 px-3 py-2 text-sm leading-6 text-slate-100 outline-none transition focus:border-lime-400"
              />
            </label>

            <label className="grid gap-2">
              <span className="text-sm font-bold text-slate-200">
                Mitigations
              </span>
              <textarea
                value={draft.mitigations}
                onChange={(event) =>
                  updateDraftField("mitigations", event.target.value)
                }
                rows={5}
                className="w-full rounded-xl border border-lime-500/25 bg-black/35 px-3 py-2 text-sm leading-6 text-slate-100 outline-none transition focus:border-lime-400"
              />
            </label>
          </section>
        </div>
      </div>
    </div>
  );
}
