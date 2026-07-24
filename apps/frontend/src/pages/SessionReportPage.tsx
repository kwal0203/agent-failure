import { ArrowLeft, Download, FileText, Save, X } from "lucide-react";
import type { MouseEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  useBeforeUnload,
  useBlocker,
  useNavigate,
  useParams,
} from "react-router-dom";
import {
  createReportDraftSnapshot,
  type EditableReportSections,
  EMPTY_REPORT_SECTIONS,
  type ReportSectionAssignment,
  useSaveSessionReportDraftMutation,
  useSessionReportDraftQuery,
} from "../query/sessionReportDraft";
import { useSessionTraceQuery } from "../query/sessionTrace";
import type {
  PutSessionReportDraftRequest,
  TimelineEvent,
} from "./session/types";

const REPORT_SECTION_OPTIONS: ReadonlyArray<{
  value: ReportSectionAssignment;
  label: string;
}> = [
  { value: "unassigned", label: "Unassigned" },
  { value: "executive_summary", label: "Executive Summary" },
  { value: "threat_model", label: "Threat Model" },
  { value: "methodology", label: "Methodology" },
  { value: "evidence_and_results", label: "Evidence & Results" },
  { value: "mitigations", label: "Mitigations" },
];

const AUTOSAVE_DEBOUNCE_MS = 1_500;

type PendingReportSave = {
  request: PutSessionReportDraftRequest;
  snapshot: string;
};

export default function SessionReportPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const traceQuery = useSessionTraceQuery(sessionId);
  const reportDraftQuery = useSessionReportDraftQuery(sessionId);
  const saveReportMutation = useSaveSessionReportDraftMutation(sessionId);
  const [draft, setDraft] = useState<EditableReportSections>(
    EMPTY_REPORT_SECTIONS,
  );
  const [error, setError] = useState<string | null>(null);
  const [selectedEventIds, setSelectedEventIds] = useState<Set<string>>(
    () => new Set(),
  );
  const [selectedEventSections, setSelectedEventSections] = useState<
    Record<string, ReportSectionAssignment>
  >({});
  const [isHydrated, setIsHydrated] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [lastSavedSnapshot, setLastSavedSnapshot] = useState<string>("");
  const hydratedSessionIdRef = useRef<string | null>(null);
  const latestSaveRef = useRef<PendingReportSave | null>(null);
  const lastSavedSnapshotRef = useRef("");
  const failedSnapshotRef = useRef<string | null>(null);
  const saveInFlightRef = useRef<Promise<boolean> | null>(null);
  const latestDraftRef = useRef(draft);
  const isHandlingBlockedNavigationRef = useRef(false);

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

  const traceError =
    traceQuery.error instanceof Error ? traceQuery.error.message : null;
  const reportDraftError =
    reportDraftQuery.error instanceof Error
      ? reportDraftQuery.error.message
      : null;
  const displayedError = error ?? reportDraftError ?? traceError;
  const loadingEvidence = reportDraftQuery.isPending || traceQuery.isPending;

  const orderedEvidence = useMemo(
    () =>
      [...(traceQuery.data?.timelineEvents ?? [])].sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      ),
    [traceQuery.data],
  );

  useEffect(() => {
    if (!sessionId || !reportDraftQuery.data || !traceQuery.data) return;
    if (hydratedSessionIdRef.current === sessionId) return;

    const selectedFromServer = new Set<string>();
    const sectionsByTimelineEventId: Record<string, ReportSectionAssignment> =
      {};
    const selectedEvidenceIds = new Set(
      reportDraftQuery.data.selectedEvidenceIds,
    );
    for (const event of orderedEvidence) {
      if (event.report_selectable !== true) continue;
      const traceEventId = toTraceEventId(event.id);
      if (!traceEventId) continue;
      if (selectedEvidenceIds.has(traceEventId)) {
        selectedFromServer.add(event.id);
        sectionsByTimelineEventId[event.id] =
          reportDraftQuery.data.evidenceSectionsById[traceEventId] ??
          "unassigned";
      }
    }
    hydratedSessionIdRef.current = sessionId;
    setDraft(reportDraftQuery.data.sections);
    setSelectedEventIds(selectedFromServer);
    setSelectedEventSections(sectionsByTimelineEventId);
    lastSavedSnapshotRef.current = reportDraftQuery.data.persistedSnapshot;
    setLastSavedSnapshot(reportDraftQuery.data.persistedSnapshot);
    setIsHydrated(true);
  }, [
    orderedEvidence,
    reportDraftQuery.data,
    sessionId,
    traceQuery.data,
    toTraceEventId,
  ]);

  const selectEvent = (eventId: string) => {
    setSelectedEventIds((prev) => {
      const next = new Set(prev);
      next.add(eventId);
      return next;
    });
    setSelectedEventSections((prevSections) => {
      const nextSections = { ...prevSections };
      if (!nextSections[eventId]) {
        nextSections[eventId] = "unassigned";
      }
      return nextSections;
    });
  };

  const removeEventSelection = (eventId: string) => {
    setSelectedEventIds((prev) => {
      const next = new Set(prev);
      next.delete(eventId);
      return next;
    });
  };

  const handleSelectableChipClick = (
    eventId: string,
    event: MouseEvent<HTMLButtonElement>,
  ) => {
    const target = event.target as HTMLElement | null;
    if (
      target?.closest(
        "select, option, label, input, textarea, [data-no-chip-toggle='true']",
      )
    ) {
      return;
    }
    selectEvent(eventId);
  };

  const setEventSection = (
    eventId: string,
    section: ReportSectionAssignment,
  ) => {
    setSelectedEventSections((prev) => ({ ...prev, [eventId]: section }));
  };

  const selectedEvidenceBySection = useMemo(() => {
    const grouped = new Map<ReportSectionAssignment, TimelineEvent[]>();
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
  const latestEvidenceBySectionRef = useRef(selectedEvidenceBySection);
  latestDraftRef.current = draft;
  latestEvidenceBySectionRef.current = selectedEvidenceBySection;

  const selectedItemsPayload = useMemo(
    () =>
      orderedEvidence
        .filter(
          (event) =>
            event.report_selectable === true && selectedEventIds.has(event.id),
        )
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
    [orderedEvidence, selectedEventIds, selectedEventSections, toTraceEventId],
  );

  const currentSnapshot = useMemo(() => {
    const selectedEvidenceIds = selectedItemsPayload.map(
      (item) => item.event_id,
    );
    const evidenceSectionsById = Object.fromEntries(
      selectedItemsPayload.map((item) => [
        item.event_id,
        item.report_section as ReportSectionAssignment,
      ]),
    );
    return createReportDraftSnapshot({
      sections: draft,
      selectedEvidenceIds,
      evidenceSectionsById,
    });
  }, [draft, selectedItemsPayload]);

  const isDirty = isHydrated && currentSnapshot !== lastSavedSnapshot;

  const currentSave = useMemo<PendingReportSave>(
    () => ({
      snapshot: currentSnapshot,
      request: {
        sections: {
          executive_summary: draft.executiveSummary,
          threat_model: draft.threatModel,
          methodology: draft.methodology,
          evidence_and_results: draft.evidenceAndResults,
          mitigations: draft.mitigations,
        },
        items: selectedItemsPayload,
      },
    }),
    [currentSnapshot, draft, selectedItemsPayload],
  );
  latestSaveRef.current = currentSave;

  const {
    error: saveMutationError,
    isError: didSaveFail,
    isPending: isSaving,
    mutateAsync: saveReport,
    reset: resetSaveMutation,
  } = saveReportMutation;

  const performSave = useCallback(
    (pendingSave: PendingReportSave): Promise<boolean> => {
      if (saveInFlightRef.current) {
        return saveInFlightRef.current;
      }

      resetSaveMutation();
      const operation = saveReport(pendingSave.request)
        .then(() => {
          failedSnapshotRef.current = null;
          lastSavedSnapshotRef.current = pendingSave.snapshot;
          setLastSavedSnapshot(pendingSave.snapshot);
          return true;
        })
        .catch(() => {
          failedSnapshotRef.current = pendingSave.snapshot;
          return false;
        })
        .finally(() => {
          saveInFlightRef.current = null;
        });
      saveInFlightRef.current = operation;
      return operation;
    },
    [resetSaveMutation, saveReport],
  );

  const flushSave = useCallback(async (): Promise<boolean> => {
    while (true) {
      const inFlightSave = saveInFlightRef.current;
      if (inFlightSave) {
        if (!(await inFlightSave)) return false;
        continue;
      }

      const latestSave = latestSaveRef.current;
      if (
        !isHydrated ||
        !latestSave ||
        latestSave.snapshot === lastSavedSnapshotRef.current
      ) {
        return true;
      }

      if (!(await performSave(latestSave))) return false;
    }
  }, [isHydrated, performSave]);

  useEffect(() => {
    if (!isDirty || isSaving) return;
    if (failedSnapshotRef.current === currentSnapshot) return;
    const scheduledSnapshot = currentSnapshot;
    const timer = window.setTimeout(() => {
      if (latestSaveRef.current?.snapshot !== scheduledSnapshot) return;
      void flushSave();
    }, AUTOSAVE_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [currentSnapshot, flushSave, isDirty, isSaving]);

  const saveError =
    saveMutationError instanceof Error ? saveMutationError.message : null;
  const saveStatus = isSaving
    ? "Saving..."
    : didSaveFail
      ? "Save failed"
      : isHydrated && !isDirty
        ? "Saved"
        : "Unsaved changes";

  const handleExport = useCallback(async () => {
    setIsExporting(true);
    try {
      const saved = await flushSave();
      if (!saved) return;
      const exportDraft = latestDraftRef.current;
      const exportEvidenceBySection = latestEvidenceBySectionRef.current;

      const { renderSessionReportPdf } = await import(
        "./report/renderSessionReportPdf"
      );
      const pdfBlob = await renderSessionReportPdf({
        sessionId: sessionId ?? "unknown",
        exportedAt: new Date(),
        sections: [
          {
            heading: "Executive Summary",
            content: exportDraft.executiveSummary,
          },
          { heading: "Threat Model", content: exportDraft.threatModel },
          {
            heading: "Exploitation Methodology",
            content: exportDraft.methodology,
          },
          {
            heading: "Evidence and Results",
            content: exportDraft.evidenceAndResults,
          },
          { heading: "Mitigations", content: exportDraft.mitigations },
        ],
        evidenceSections: REPORT_SECTION_OPTIONS.map((section) => ({
          heading: section.label,
          evidence: (exportEvidenceBySection.get(section.value) ?? []).map(
            (event) => ({ id: event.id, title: event.title }),
          ),
        })),
      });
      const url = URL.createObjectURL(pdfBlob);
      const link = document.createElement("a");
      const datePart = new Date().toISOString().slice(0, 10);
      link.href = url;
      link.download = `session-report-${sessionId ?? "unknown"}-${datePart}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (exportError) {
      setError(
        exportError instanceof Error
          ? `Failed to export report: ${exportError.message}`
          : "Failed to export report",
      );
    } finally {
      setIsExporting(false);
    }
  }, [flushSave, sessionId]);

  useBeforeUnload(
    useCallback(
      (event) => {
        if (!isDirty) return;
        event.preventDefault();
        event.returnValue = "";
      },
      [isDirty],
    ),
  );

  const navigationBlocker = useBlocker(isDirty);
  useEffect(() => {
    if (
      navigationBlocker.state !== "blocked" ||
      isHandlingBlockedNavigationRef.current
    ) {
      return;
    }
    isHandlingBlockedNavigationRef.current = true;

    if (!window.confirm("Save your report changes and leave this page?")) {
      navigationBlocker.reset();
      isHandlingBlockedNavigationRef.current = false;
      return;
    }

    void flushSave().then((saved) => {
      if (saved) {
        navigationBlocker.proceed();
      } else {
        navigationBlocker.reset();
      }
      isHandlingBlockedNavigationRef.current = false;
    });
  }, [flushSave, navigationBlocker]);

  const updateDraftField = <K extends keyof EditableReportSections>(
    key: K,
    value: EditableReportSections[K],
  ) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="min-h-full bg-black font-sans text-slate-100">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-5 pt-5 pb-8 text-[17px] md:px-8 lg:px-10">
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => {
              navigate("/reports");
            }}
            className="inline-flex items-center gap-2 rounded-lg border border-lime-500/35 bg-black/40 px-3 py-2 text-xs font-bold uppercase tracking-wide text-lime-200 transition hover:bg-lime-500/10"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Reports
          </button>
          <div className="flex items-center gap-2">
            <span
              role="status"
              className={`text-xs font-semibold ${
                didSaveFail
                  ? "text-rose-300"
                  : isSaving
                    ? "text-amber-300"
                    : "text-slate-400"
              }`}
            >
              {saveStatus}
            </span>
            <button
              type="button"
              onClick={() => {
                void flushSave();
              }}
              disabled={!isDirty || isSaving}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-500/40 bg-slate-900/50 px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-300 disabled:opacity-60"
              title={isDirty ? "Save report changes" : "No unsaved changes"}
            >
              <Save className="h-4 w-4" />
              {isSaving ? "Saving..." : "Save"}
            </button>
            <button
              type="button"
              onClick={() => {
                void handleExport();
              }}
              disabled={isSaving || isExporting}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-500/40 bg-slate-900/50 px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-300 disabled:opacity-60"
              title="Auto-saves, then exports PDF."
            >
              <Download className="h-4 w-4" />
              {isExporting ? "Exporting..." : "Export"}
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
            {displayedError ? (
              <p className="mb-3 rounded-lg border border-rose-500/45 bg-rose-950/25 px-3 py-2 text-sm text-rose-200">
                {displayedError}
              </p>
            ) : null}
            {saveError ? (
              <p className="mb-3 rounded-lg border border-rose-500/45 bg-rose-950/25 px-3 py-2 text-sm text-rose-200">
                {saveError}
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
                  const chipBody = (
                    <div className="relative flex flex-col items-start gap-0">
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
                        onClick={(clickEvent) => {
                          if (isSelected) {
                            removeEventSelection(event.id);
                          } else {
                            handleSelectableChipClick(event.id, clickEvent);
                          }
                        }}
                        className={`w-full cursor-pointer rounded-lg px-2.5 py-2.5 text-left ${tone.chipClass} ${
                          isSelected ? "brightness-[1.08]" : ""
                        }`}
                        style={
                          isSelected
                            ? {
                                boxShadow:
                                  "0 0 0 1px rgba(255, 255, 255, 0.12)",
                              }
                            : undefined
                        }
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
                              className="flex items-center gap-2 rounded border border-slate-500/30 bg-black/35 px-2 py-1 text-xs text-slate-200"
                            >
                              <span className="min-w-0 flex-1 truncate">
                                {event.title}
                              </span>
                              <select
                                value={
                                  selectedEventSections[event.id] ??
                                  "unassigned"
                                }
                                onChange={(selectEvent) => {
                                  setEventSection(
                                    event.id,
                                    selectEvent.target
                                      .value as ReportSectionAssignment,
                                  );
                                }}
                                aria-label={`Assign section for ${event.title}`}
                                className="max-w-[8.5rem] rounded border border-slate-500/40 bg-slate-900/90 px-1.5 py-0.5 text-[11px] font-semibold text-slate-100 outline-none"
                              >
                                {REPORT_SECTION_OPTIONS.map((option) => (
                                  <option
                                    key={option.value}
                                    value={option.value}
                                  >
                                    {option.label}
                                  </option>
                                ))}
                              </select>
                              <button
                                type="button"
                                onClick={() => removeEventSelection(event.id)}
                                aria-label={`Remove ${event.title} from evidence`}
                                title="Remove evidence"
                                className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-rose-500/40 bg-rose-950/30 text-rose-200 hover:bg-rose-900/40"
                              >
                                <X className="h-3 w-3" />
                              </button>
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
