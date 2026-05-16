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
    <div style={{ display: "grid", gap: 16 }}>
      <div
        style={{ display: "flex", justifyContent: "space-between", gap: 12 }}
      >
        <h1 style={{ margin: 0, fontSize: 24, color: "#d7ffd7" }}>
          Pilot Requests
        </h1>
        <div style={{ display: "flex", gap: 8 }}>
          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value as StatusFilter)}
            style={{
              background: "#0d1a0d",
              color: "#d7ffd7",
              border: "1px solid #2e7d32",
              borderRadius: 8,
              padding: "8px 10px",
            }}
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
            style={{
              background: "#112a11",
              color: "#b6ffb9",
              border: "1px solid #2e7d32",
              borderRadius: 8,
              padding: "8px 12px",
              cursor: "pointer",
            }}
          >
            Refresh
          </button>
        </div>
      </div>

      {loading ? <p>Loading...</p> : null}
      {error ? <p style={{ color: "#ffb3bf" }}>{error}</p> : null}

      {!loading ? (
        <div
          style={{
            overflowX: "auto",
            border: "1px solid #1b5e20",
            borderRadius: 10,
          }}
        >
          <table
            style={{ width: "100%", borderCollapse: "collapse", minWidth: 980 }}
          >
            <thead>
              <tr style={{ background: "#0b180b", color: "#9dc6a2" }}>
                <th style={{ textAlign: "left", padding: "10px 12px" }}>
                  Created
                </th>
                <th style={{ textAlign: "left", padding: "10px 12px" }}>
                  Name
                </th>
                <th style={{ textAlign: "left", padding: "10px 12px" }}>
                  Email
                </th>
                <th style={{ textAlign: "left", padding: "10px 12px" }}>
                  University
                </th>
                <th style={{ textAlign: "left", padding: "10px 12px" }}>
                  Status
                </th>
                <th style={{ textAlign: "left", padding: "10px 12px" }}>
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.requestId}
                  style={{ borderTop: "1px solid #163316" }}
                >
                  <td style={{ padding: "10px 12px", color: "#9dc6a2" }}>
                    {new Date(item.createdAt).toLocaleString()}
                  </td>
                  <td style={{ padding: "10px 12px" }}>{item.fullName}</td>
                  <td style={{ padding: "10px 12px" }}>{item.workEmail}</td>
                  <td style={{ padding: "10px 12px" }}>{item.university}</td>
                  <td style={{ padding: "10px 12px" }}>{item.status}</td>
                  <td style={{ padding: "10px 12px" }}>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {nextStatuses[item.status].map((status) => (
                        <button
                          key={status}
                          type="button"
                          disabled={!canEdit || updatingId === item.requestId}
                          onClick={() => void onUpdateStatus(item, status)}
                          style={{
                            background: "#102810",
                            color: "#b6ffb9",
                            border: "1px solid #2e7d32",
                            borderRadius: 8,
                            padding: "6px 10px",
                            cursor: "pointer",
                            opacity:
                              !canEdit || updatingId === item.requestId
                                ? 0.6
                                : 1,
                          }}
                        >
                          Mark {status}
                        </button>
                      ))}
                      {nextStatuses[item.status].length === 0 ? (
                        <span>Final</span>
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
