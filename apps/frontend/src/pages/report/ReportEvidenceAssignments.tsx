import { X } from "lucide-react";
import type { ReportSectionAssignment } from "../../query/sessionReportDraft";
import { type EvidenceBySection, REPORT_SECTION_OPTIONS } from "./reportModel";

export function ReportEvidenceAssignments({
  evidenceBySection,
  onRemove,
  onSectionChange,
  selectedEventSections,
}: {
  evidenceBySection: EvidenceBySection;
  onRemove: (eventId: string) => void;
  onSectionChange: (eventId: string, section: ReportSectionAssignment) => void;
  selectedEventSections: Record<string, ReportSectionAssignment>;
}) {
  return (
    <div className="rounded-xl border border-slate-600/30 bg-black/25 p-3">
      <p className="mb-3 text-xs font-black uppercase tracking-wide text-slate-300">
        Evidence By Section
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        {REPORT_SECTION_OPTIONS.map((sectionOption) => {
          const events = evidenceBySection.get(sectionOption.value) ?? [];
          return (
            <div
              key={sectionOption.value}
              className="rounded-lg border border-slate-600/35 bg-slate-900/35 p-2.5"
            >
              <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-300">
                {sectionOption.label}
              </p>
              {events.length === 0 ? (
                <p className="text-xs text-slate-500">No evidence assigned</p>
              ) : (
                <div className="space-y-1">
                  {events.map((event) => (
                    <div
                      key={event.id}
                      className="flex items-center gap-2 rounded border border-slate-500/30 bg-black/35 px-2 py-1 text-xs text-slate-200"
                    >
                      <span className="min-w-0 flex-1 truncate">
                        {event.title}
                      </span>
                      <select
                        value={selectedEventSections[event.id] ?? "unassigned"}
                        onChange={(selectEvent) =>
                          onSectionChange(
                            event.id,
                            selectEvent.target.value as ReportSectionAssignment,
                          )
                        }
                        aria-label={`Assign section for ${event.title}`}
                        className="max-w-[8.5rem] rounded border border-slate-500/40 bg-slate-900/90 px-1.5 py-0.5 text-[11px] font-semibold text-slate-100 outline-none"
                      >
                        {REPORT_SECTION_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => onRemove(event.id)}
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
  );
}
