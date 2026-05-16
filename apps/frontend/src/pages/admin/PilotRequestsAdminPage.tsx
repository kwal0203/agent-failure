import { useCallback, useEffect, useMemo, useState } from "react";
import {
  listPilotRequests,
  type PilotRequestItem,
  updatePilotRequestStatus,
} from "../../auth/pilotRequests";

type StatusFilter = "all" | "new" | "contacted" | "approved" | "rejected";

const nextStatuses: Record<
  PilotRequestItem["status"],
  PilotRequestItem["status"][]
> = {
  new: ["contacted"],
  contacted: ["approved", "rejected"],
  approved: [],
  rejected: [],
};

export default function PilotRequestsAdminPage() {
  const [items, setItems] = useState<PilotRequestItem[]>([]);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listPilotRequests({
        status: filter === "all" ? undefined : filter,
        limit: 100,
        offset: 0,
      });
      setItems(data.items);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Failed to load pilot requests.",
      );
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);

  const canEdit = useMemo(() => !loading && !error, [loading, error]);

  const onUpdateStatus = async (
    item: PilotRequestItem,
    nextStatus: PilotRequestItem["status"],
  ) => {
    setUpdatingId(item.requestId);
    setError(null);
    try {
      const updated = await updatePilotRequestStatus(
        item.requestId,
        nextStatus,
      );
      setItems((prev) =>
        prev.map((current) =>
          current.requestId === updated.requestId ? updated : current,
        ),
      );
    } catch (updateError) {
      setError(
        updateError instanceof Error
          ? updateError.message
          : "Failed to update pilot request.",
      );
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="grid gap-4 text-slate-100">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="m-0 font-heading text-2xl font-semibold tracking-wide text-lime-200">
          Pilot Requests
        </h1>
        <div className="flex items-center gap-2">
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value as StatusFilter)}
            className="rounded-md border border-lime-500/35 bg-black/60 px-3 py-2 text-sm text-lime-100 outline-none ring-0 transition focus:border-lime-400"
          >
            <option value="all">All statuses</option>
            <option value="new">New</option>
            <option value="contacted">Contacted</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
          <button
            type="button"
            onClick={() => void load()}
            className="rounded-md border border-lime-500/40 bg-lime-950/40 px-3 py-2 text-sm font-semibold text-lime-100 transition hover:bg-lime-900/40"
          >
            Refresh
          </button>
        </div>
      </div>

      {loading ? <p className="text-lime-300/85">Loading...</p> : null}
      {error ? <p className="text-rose-200">{error}</p> : null}

      {!loading ? (
        <div className="overflow-x-auto rounded-xl border border-lime-700/60 bg-black/35 shadow-[0_0_28px_rgba(34,197,94,0.08)]">
          <table className="min-w-[980px] w-full border-collapse text-sm">
            <thead>
              <tr className="bg-lime-950/35 text-lime-200/85">
                <th className="px-3 py-2 text-left font-semibold">Created</th>
                <th className="px-3 py-2 text-left font-semibold">Name</th>
                <th className="px-3 py-2 text-left font-semibold">Email</th>
                <th className="px-3 py-2 text-left font-semibold">
                  University
                </th>
                <th className="px-3 py-2 text-left font-semibold">Status</th>
                <th className="px-3 py-2 text-left font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.requestId}
                  className="border-t border-lime-900/70 text-slate-100"
                >
                  <td className="px-3 py-2 text-lime-100/80">
                    {new Date(item.createdAt).toLocaleString()}
                  </td>
                  <td className="px-3 py-2">{item.fullName}</td>
                  <td className="px-3 py-2">{item.workEmail}</td>
                  <td className="px-3 py-2">{item.university}</td>
                  <td className="px-3 py-2">
                    <span className="rounded border border-lime-500/30 bg-lime-500/10 px-2 py-1 text-xs font-semibold uppercase tracking-wide text-lime-200">
                      {item.status}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-2">
                      {nextStatuses[item.status].map((status) => (
                        <button
                          key={status}
                          type="button"
                          disabled={!canEdit || updatingId === item.requestId}
                          onClick={() => void onUpdateStatus(item, status)}
                          className="rounded-md border border-lime-500/35 bg-lime-950/30 px-2.5 py-1.5 text-xs font-semibold text-lime-100 transition enabled:hover:bg-lime-900/45 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Mark {status}
                        </button>
                      ))}
                      {nextStatuses[item.status].length === 0 ? (
                        <span className="text-xs text-slate-400">Final</span>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
