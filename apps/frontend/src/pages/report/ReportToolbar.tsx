import { ArrowLeft, Download, Save } from "lucide-react";

export function ReportToolbar({
  didSaveFail,
  isDirty,
  isExporting,
  isSaving,
  onBack,
  onExport,
  onSave,
  saveStatus,
}: {
  didSaveFail: boolean;
  isDirty: boolean;
  isExporting: boolean;
  isSaving: boolean;
  onBack: () => void;
  onExport: () => void;
  onSave: () => void;
  saveStatus: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <button
        type="button"
        onClick={onBack}
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
          onClick={onSave}
          disabled={!isDirty || isSaving}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-500/40 bg-slate-900/50 px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-300 disabled:opacity-60"
          title={isDirty ? "Save report changes" : "No unsaved changes"}
        >
          <Save className="h-4 w-4" />
          {isSaving ? "Saving..." : "Save"}
        </button>
        <button
          type="button"
          onClick={onExport}
          disabled={isSaving || isExporting}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-500/40 bg-slate-900/50 px-3 py-2 text-xs font-bold uppercase tracking-wide text-slate-300 disabled:opacity-60"
          title="Auto-saves, then exports PDF."
        >
          <Download className="h-4 w-4" />
          {isExporting ? "Exporting..." : "Export"}
        </button>
      </div>
    </div>
  );
}
