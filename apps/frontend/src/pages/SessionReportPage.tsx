import { ArrowLeft, Download, FileText, Sparkles } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type {
  GetSessionReportEvidenceResponse,
  ImportSelectedEvidenceResponse,
  ReportEvidenceItem,
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

function buildEvidenceSummary(items: ReportEvidenceItem[]): string {
  if (items.length === 0) return "";
  return items
    .map((item) => {
      const citation = item.citation_label ?? `E${item.position + 1}`;
      const timestamp = new Date(item.occurred_at).toLocaleString();
      const description = item.description ? ` — ${item.description}` : "";
      return `[${citation}] ${item.title}${description} (${timestamp})`;
    })
    .join("\n");
}

export default function SessionReportPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [draft, setDraft] = useState<DraftSections>(DEFAULT_DRAFT);
  const [evidenceItems, setEvidenceItems] = useState<ReportEvidenceItem[]>([]);
  const [loadingEvidence, setLoadingEvidence] = useState(true);
  const [importingEvidence, setImportingEvidence] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshEvidence = useCallback(async () => {
    if (!sessionId) return;
    setLoadingEvidence(true);
    setError(null);
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
        throw new Error(`Failed to load evidence (HTTP ${response.status})`);
      }
      const payload =
        (await response.json()) as GetSessionReportEvidenceResponse;
      setEvidenceItems(Array.isArray(payload.items) ? payload.items : []);
    } catch (fetchError) {
      setError(
        fetchError instanceof Error ? fetchError.message : "Unknown error",
      );
    } finally {
      setLoadingEvidence(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void refreshEvidence();
  }, [refreshEvidence]);

  const orderedEvidence = useMemo(
    () => [...evidenceItems].sort((a, b) => a.position - b.position),
    [evidenceItems],
  );

  const importSelectedEvidence = useCallback(async () => {
    if (!sessionId) return;
    setImportingEvidence(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/api/v1/sessions/${sessionId}/report/import-selected-evidence`,
        {
          method: "POST",
          headers: {
            Authorization: getAuthHeader(),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({}),
        },
      );
      if (!response.ok) {
        throw new Error(`Import failed (HTTP ${response.status})`);
      }
      const payload = (await response.json()) as ImportSelectedEvidenceResponse;
      const imported = Array.isArray(payload.items) ? payload.items : [];
      const ordered = [...imported].sort((a, b) => a.position - b.position);
      setEvidenceItems(ordered);
      setDraft((prev) => ({
        ...prev,
        evidenceAndResults: buildEvidenceSummary(ordered),
      }));
    } catch (importError) {
      setError(
        importError instanceof Error ? importError.message : "Unknown error",
      );
    } finally {
      setImportingEvidence(false);
    }
  }, [sessionId]);

  const updateDraftField = <K extends keyof DraftSections>(
    key: K,
    value: DraftSections[K],
  ) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="min-h-full bg-black font-sans text-slate-100">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-5 py-6 md:px-8 lg:px-10">
        <header className="rounded-2xl border border-lime-500/20 bg-slate-950/70 p-4 shadow-[0_0_26px_rgba(132,204,22,0.14)]">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => navigate(`/sessions/${sessionId ?? ""}`)}
                className="inline-flex items-center gap-2 rounded-lg border border-lime-500/35 bg-black/40 px-3 py-2 text-xs font-bold uppercase tracking-wide text-lime-200 transition hover:bg-lime-500/10"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Session
              </button>
              <div className="rounded-lg border border-lime-400/35 bg-lime-500/10 p-2 text-lime-200">
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <h1 className="m-0 text-xl font-extrabold tracking-tight text-slate-100 md:text-2xl">
                  Lab Report Draft
                </h1>
                <p className="mt-1 text-sm text-slate-400">
                  Session evidence import and report authoring
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => void importSelectedEvidence()}
                disabled={importingEvidence || !sessionId}
                className="inline-flex items-center gap-2 rounded-lg border border-lime-500/40 bg-lime-950/40 px-3 py-2 text-xs font-bold uppercase tracking-wide text-lime-100 transition hover:bg-lime-900/50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Sparkles className="h-4 w-4" />
                {importingEvidence
                  ? "Importing..."
                  : "Import Selected Evidence"}
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
          {error ? (
            <p className="mt-3 rounded-lg border border-rose-500/45 bg-rose-950/25 px-3 py-2 text-sm text-rose-200">
              {error}
            </p>
          ) : null}
        </header>

        <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="rounded-2xl border border-lime-500/20 bg-slate-950/65 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="m-0 text-sm font-black uppercase tracking-wide text-lime-300">
                Selected Evidence
              </h2>
              <span className="rounded-md border border-lime-500/35 bg-lime-500/10 px-2 py-1 text-xs font-bold text-lime-200">
                {orderedEvidence.length}
              </span>
            </div>
            <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
              {loadingEvidence ? (
                <p className="text-sm text-slate-400">Loading evidence...</p>
              ) : orderedEvidence.length === 0 ? (
                <p className="text-sm text-slate-400">
                  No selected evidence yet. Go to session timeline and select
                  relevant events, then import here.
                </p>
              ) : (
                orderedEvidence.map((item) => (
                  <article
                    key={item.event_id}
                    className="rounded-xl border border-lime-500/20 bg-black/35 p-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="m-0 text-sm font-bold text-slate-100">
                        {item.citation_label ?? `E${item.position + 1}`} ·{" "}
                        {item.title}
                      </p>
                      <span className="rounded border border-lime-500/30 bg-lime-500/10 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-lime-200">
                        {item.evidence_type.replace("_", " ")}
                      </span>
                    </div>
                    {item.description ? (
                      <p className="mt-2 text-xs leading-5 text-slate-300">
                        {item.description}
                      </p>
                    ) : null}
                  </article>
                ))
              )}
            </div>
          </aside>

          <section className="space-y-4 rounded-2xl border border-lime-500/20 bg-slate-950/65 p-4">
            <h2 className="m-0 text-sm font-black uppercase tracking-wide text-lime-300">
              Report Draft
            </h2>

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
