import { ArrowLeft } from "lucide-react";
import { useMemo } from "react";
import { useNavigate, useParams } from "react-router";
import type { PersistedReportDraft } from "../query/sessionReportDraft";
import { useSessionReportDraftQuery } from "../query/sessionReportDraft";
import { useSessionTraceQuery } from "../query/sessionTrace";
import { ReportDraftEditor } from "./report/ReportDraftEditor";
import { ReportEvidenceAssignments } from "./report/ReportEvidenceAssignments";
import { ReportEvidencePanel } from "./report/ReportEvidencePanel";
import { ReportToolbar } from "./report/ReportToolbar";
import { useReportAutosave } from "./report/useReportAutosave";
import { useReportEditor } from "./report/useReportEditor";
import { useReportNavigationGuard } from "./report/useReportNavigationGuard";
import { useReportPdfExport } from "./report/useReportPdfExport";
import type { TimelineEvent } from "./session/types";

function ReportPageLoading({
  error,
  onBack,
}: {
  error: string | null;
  onBack: () => void;
}) {
  return (
    <div className="min-h-full bg-black font-sans text-slate-100">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-5 pt-5 pb-8 text-[17px] md:px-8 lg:px-10">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex w-fit items-center gap-2 rounded-lg border border-lime-500/35 bg-black/40 px-3 py-2 text-xs font-bold uppercase tracking-wide text-lime-200 transition hover:bg-lime-500/10"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Reports
        </button>
        <ReportEvidencePanel
          error={error}
          evidence={[]}
          isLoading={!error}
          onRemove={() => undefined}
          onSelect={() => undefined}
          saveError={null}
          selectedEventIds={new Set()}
        />
      </div>
    </div>
  );
}

function SessionReportWorkspace({
  orderedEvidence,
  persistedDraft,
  queryError,
  sessionId,
}: {
  orderedEvidence: TimelineEvent[];
  persistedDraft: PersistedReportDraft;
  queryError: string | null;
  sessionId: string;
}) {
  const navigate = useNavigate();
  const editor = useReportEditor({ orderedEvidence, persistedDraft });
  const autosave = useReportAutosave({
    currentSave: editor.currentSave,
    hydratedSnapshot: editor.hydratedSnapshot,
    sessionId,
  });
  useReportNavigationGuard({
    flushSave: autosave.flushSave,
    isDirty: autosave.isDirty,
  });
  const pdfExport = useReportPdfExport({
    draft: editor.draft,
    evidenceBySection: editor.selectedEvidenceBySection,
    flushSave: autosave.flushSave,
    sessionId,
  });

  return (
    <div className="min-h-full bg-black font-sans text-slate-100">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 px-5 pt-5 pb-8 text-[17px] md:px-8 lg:px-10">
        <ReportToolbar
          didSaveFail={autosave.didSaveFail}
          isDirty={autosave.isDirty}
          isExporting={pdfExport.isExporting}
          isSaving={autosave.isSaving}
          onBack={() => navigate("/reports")}
          onExport={() => void pdfExport.exportReport()}
          onSave={() => void autosave.flushSave()}
          saveStatus={autosave.saveStatus}
        />

        <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
          <ReportEvidencePanel
            error={pdfExport.error ?? queryError}
            evidence={orderedEvidence}
            isLoading={false}
            onRemove={editor.removeEventSelection}
            onSelect={editor.selectEvent}
            saveError={autosave.saveError}
            selectedEventIds={editor.selectedEventIds}
          />

          <section className="space-y-4 rounded-2xl border border-lime-500/20 bg-slate-950/65 p-4">
            <h2 className="m-0 text-sm font-black uppercase tracking-wide text-lime-300">
              Report Draft
            </h2>
            <ReportEvidenceAssignments
              evidenceBySection={editor.selectedEvidenceBySection}
              onRemove={editor.removeEventSelection}
              onSectionChange={editor.setEventSection}
              selectedEventSections={editor.selectedEventSections}
            />
            <ReportDraftEditor
              draft={editor.draft}
              onChange={editor.updateDraftField}
            />
          </section>
        </div>
      </div>
    </div>
  );
}

export default function SessionReportPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const traceQuery = useSessionTraceQuery(sessionId);
  const reportDraftQuery = useSessionReportDraftQuery(sessionId);
  const orderedEvidence = useMemo(
    () =>
      [...(traceQuery.data?.timelineEvents ?? [])].sort(
        (a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      ),
    [traceQuery.data],
  );
  const queryError =
    reportDraftQuery.error instanceof Error
      ? reportDraftQuery.error.message
      : traceQuery.error instanceof Error
        ? traceQuery.error.message
        : null;

  if (!sessionId || !traceQuery.data || !reportDraftQuery.data) {
    return (
      <ReportPageLoading
        error={queryError}
        onBack={() => navigate("/reports")}
      />
    );
  }

  return (
    <SessionReportWorkspace
      key={sessionId}
      orderedEvidence={orderedEvidence}
      persistedDraft={reportDraftQuery.data}
      queryError={queryError}
      sessionId={sessionId}
    />
  );
}
