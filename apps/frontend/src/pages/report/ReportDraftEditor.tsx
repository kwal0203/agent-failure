import type { EditableReportSections } from "../../query/sessionReportDraft";

const REPORT_FIELDS: ReadonlyArray<{
  key: keyof EditableReportSections;
  label: string;
  rows: number;
}> = [
  { key: "executiveSummary", label: "Executive Summary", rows: 5 },
  { key: "threatModel", label: "Threat Model", rows: 5 },
  {
    key: "methodology",
    label: "Exploitation Methodology",
    rows: 6,
  },
  {
    key: "evidenceAndResults",
    label: "Evidence and Results",
    rows: 8,
  },
  { key: "mitigations", label: "Mitigations", rows: 5 },
];

export function ReportDraftEditor({
  draft,
  onChange,
}: {
  draft: EditableReportSections;
  onChange: <K extends keyof EditableReportSections>(
    key: K,
    value: EditableReportSections[K],
  ) => void;
}) {
  return (
    <>
      {REPORT_FIELDS.map((field) => (
        <label key={field.key} className="grid gap-2">
          <span className="text-sm font-bold text-slate-200">
            {field.label}
          </span>
          <textarea
            value={draft[field.key]}
            onChange={(event) => onChange(field.key, event.target.value)}
            rows={field.rows}
            className="w-full rounded-xl border border-lime-500/25 bg-black/35 px-3 py-2 text-sm leading-6 text-slate-100 outline-none transition focus:border-lime-400"
          />
        </label>
      ))}
    </>
  );
}
