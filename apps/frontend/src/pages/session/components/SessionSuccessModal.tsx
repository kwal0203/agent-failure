import { formatTime } from "../helpers";

type SessionSuccessModalProps = {
  completedAt: string | null;
  onReturnToCatalog: () => void;
};

export function SessionSuccessModal({
  completedAt,
  onReturnToCatalog,
}: SessionSuccessModalProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Session completion success"
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-slate-950/65 p-4"
    >
      <section className="relative w-full max-w-[560px] rounded-2xl border border-emerald-700 bg-gradient-to-br from-emerald-950/95 to-slate-950/95 px-5 pb-5 pt-4 text-emerald-100 shadow-[0_16px_40px_rgba(0,0,0,0.42)]">
        <div
          aria-hidden="true"
          className="mx-auto mb-3 mt-0.5 flex h-[72px] w-[72px] items-center justify-center rounded-full border-2 border-emerald-300 bg-emerald-800/45 text-4xl font-extrabold text-emerald-200"
        >
          ✓
        </div>
        <h2 className="mb-2.5 mt-0 text-center text-2xl font-semibold text-emerald-100">
          Lab completed successfully
        </h2>
        <p className="mb-2 mt-0 text-center text-emerald-200">
          All required objectives are complete.
        </p>
        {completedAt ? (
          <p className="mb-1 mt-0 text-center opacity-90">
            Completed at {formatTime(completedAt)}
          </p>
        ) : null}
        <div className="mt-3.5 flex justify-center">
          <button
            type="button"
            onClick={onReturnToCatalog}
            className="cursor-pointer rounded-[10px] border border-emerald-300 bg-emerald-800/45 px-3.5 py-2 font-bold text-emerald-100 hover:bg-emerald-700/45"
          >
            Return to Catalog
          </button>
        </div>
      </section>
    </div>
  );
}
