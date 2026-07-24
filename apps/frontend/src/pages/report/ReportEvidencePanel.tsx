import { FileText } from "lucide-react";
import type { TimelineEvent } from "../session/types";
import { eventTone } from "./reportModel";

export function ReportEvidencePanel({
  error,
  evidence,
  isLoading,
  onRemove,
  onSelect,
  saveError,
  selectedEventIds,
}: {
  error: string | null;
  evidence: TimelineEvent[];
  isLoading: boolean;
  onRemove: (eventId: string) => void;
  onSelect: (eventId: string) => void;
  saveError: string | null;
  selectedEventIds: Set<string>;
}) {
  return (
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
      {saveError ? (
        <p className="mb-3 rounded-lg border border-rose-500/45 bg-rose-950/25 px-3 py-2 text-sm text-rose-200">
          {saveError}
        </p>
      ) : null}
      <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
        {isLoading ? (
          <p className="text-sm text-slate-400">Loading evidence...</p>
        ) : evidence.length === 0 ? (
          <p className="text-sm text-slate-400">
            No evidence found for this session in database.
          </p>
        ) : (
          evidence.map((event) => {
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
                  onClick={() =>
                    isSelected ? onRemove(event.id) : onSelect(event.id)
                  }
                  className={`w-full cursor-pointer rounded-lg px-2.5 py-2.5 text-left ${tone.chipClass} ${
                    isSelected ? "brightness-[1.08]" : ""
                  }`}
                  style={
                    isSelected
                      ? {
                          boxShadow: "0 0 0 1px rgba(255, 255, 255, 0.12)",
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
  );
}
