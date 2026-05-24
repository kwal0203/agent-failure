import { ArrowLeft, Download, FileText, Save } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type {
  GetSessionReportEvidenceResponse,
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

export default function SessionReportPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const [draft, setDraft] = useState<DraftSections>(DEFAULT_DRAFT);
  const [evidenceItems, setEvidenceItems] = useState<ReportEvidenceItem[]>([]);
  const [loadingEvidence, setLoadingEvidence] = useState(true);
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
