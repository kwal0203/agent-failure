import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import {
  type ApproveAndProvisionResponse,
  approveAndProvisionPilotRequest,
  listPilotRequests,
  type PilotRequestItem,
  type ProvisionPilotResponse,
  provisionPilotRequest,
  updatePilotRequestStatus,
} from "../../auth/pilotRequests";

type StatusFilter =
  | "all"
  | "new"
  | "contacted"
  | "approved"
  | "approved_provisioning_failed"
  | "rejected";

const nextStatuses: Record<
  PilotRequestItem["status"],
  PilotRequestItem["status"][]
> = {
  new: ["contacted"],
  contacted: ["approved", "rejected"],
  approved: [],
  approved_provisioning_failed: ["approved"],
  rejected: [],
};

export default function PilotRequestsAdminPage() {
  const [items, setItems] = useState<PilotRequestItem[]>([]);
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [provisioningId, setProvisioningId] = useState<string | null>(null);
  const [provisioningResult, setProvisioningResult] =
    useState<ApproveAndProvisionResponse | null>(null);
  const [manualProvisioningId, setManualProvisioningId] = useState<
    string | null
  >(null);
  const [manualProvisioningResult, setManualProvisioningResult] =
    useState<ProvisionPilotResponse | null>(null);
  const [expandedProvisioningId, setExpandedProvisioningId] = useState<
    string | null
  >(null);
  const [courseIdByRequestId, setCourseIdByRequestId] = useState<
    Record<string, string>
  >({});
  const [courseNameByRequestId, setCourseNameByRequestId] = useState<
    Record<string, string>
  >({});
  const [instructorEmailByRequestId, setInstructorEmailByRequestId] = useState<
    Record<string, string>
  >({});
  const [cohortSizeByRequestId, setCohortSizeByRequestId] = useState<
    Record<string, string>
  >({});
  const [classCodeModeByRequestId, setClassCodeModeByRequestId] = useState<
    Record<string, "auto" | "custom">
  >({});
  const [classCodeByRequestId, setClassCodeByRequestId] = useState<
    Record<string, string>
  >({});

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

  const buildProvisioningPayload = (item: PilotRequestItem) => {
    const baseCourseName = item.courseName?.trim() || "Pilot Course";
    const courseSlug = baseCourseName
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 48);
    const courseId = `${courseSlug || "pilot-course"}-${item.requestId.slice(0, 8)}`;
    const classCodeSeed = (item.courseName?.trim() || "PILOT")
      .toUpperCase()
      .replace(/[^A-Z0-9]+/g, "")
      .slice(0, 8);
    const classCode = `${classCodeSeed || "PILOT"}-${item.requestId
      .slice(0, 4)
      .toUpperCase()}`;
    return {
      courseId,
      courseName: baseCourseName,
      classCode,
      instructorEmail: item.workEmail,
      classCodeMaxUses:
        typeof item.cohortSize === "number" && item.cohortSize > 0
          ? Math.max(item.cohortSize * 2, item.cohortSize + 20)
          : 200,
      createInstructorIfMissing: true,
    };
  };

  const getDefaultProvisioningValues = (item: PilotRequestItem) => {
    const payload = buildProvisioningPayload(item);
    return {
      courseId: payload.courseId,
      courseName: payload.courseName,
      instructorEmail: payload.instructorEmail,
      cohortSize:
        typeof item.cohortSize === "number" && item.cohortSize > 0
          ? String(item.cohortSize)
          : "",
      classCode: payload.classCode,
    };
  };

  const getFormValues = (item: PilotRequestItem) => {
    const defaults = getDefaultProvisioningValues(item);
    return {
      courseId: courseIdByRequestId[item.requestId] ?? defaults.courseId,
      courseName: courseNameByRequestId[item.requestId] ?? defaults.courseName,
      instructorEmail:
        instructorEmailByRequestId[item.requestId] ?? defaults.instructorEmail,
      cohortSize: cohortSizeByRequestId[item.requestId] ?? defaults.cohortSize,
      classCodeMode: classCodeModeByRequestId[item.requestId] ?? "auto",
      classCode: classCodeByRequestId[item.requestId] ?? defaults.classCode,
    };
  };

  const buildClassCode = (baseText: string, requestId: string): string => {
    const classCodeSeed = (baseText.trim() || "PILOT")
      .toUpperCase()
      .replace(/[^A-Z0-9]+/g, "")
      .slice(0, 8);
    return `${classCodeSeed || "PILOT"}-${requestId.slice(0, 4).toUpperCase()}`;
  };

  const onManualProvision = async (item: PilotRequestItem) => {
    const values = getFormValues(item);
    const parsedCohortSize = Number.parseInt(values.cohortSize, 10);
    const classCodeMaxUses =
      Number.isFinite(parsedCohortSize) && parsedCohortSize > 0
        ? Math.max(parsedCohortSize * 2, parsedCohortSize + 20)
        : undefined;

    const payload = {
      courseId: values.courseId.trim(),
      courseName: values.courseName.trim(),
      classCode:
        values.classCodeMode === "custom"
          ? values.classCode.trim()
          : buildClassCode(values.courseName, item.requestId),
      instructorEmail: values.instructorEmail.trim(),
      maxUses: classCodeMaxUses,
    };

    if (
      payload.courseId.length === 0 ||
      payload.courseName.length === 0 ||
      payload.instructorEmail.length === 0 ||
      payload.classCode.length === 0
    ) {
      setError("All provisioning fields are required.");
      return;
    }

    setManualProvisioningId(item.requestId);
    setManualProvisioningResult(null);
    setError(null);
    try {
      const response = await provisionPilotRequest(item.requestId, payload);
      setManualProvisioningResult(response);
    } catch (provisionError) {
      setError(
        provisionError instanceof Error
          ? provisionError.message
          : "Failed to provision pilot request.",
      );
    } finally {
      setManualProvisioningId(null);
    }
  };

  const onApproveAndProvision = async (item: PilotRequestItem) => {
    setProvisioningId(item.requestId);
    setError(null);
    setProvisioningResult(null);
    try {
      const response = await approveAndProvisionPilotRequest(
        item.requestId,
        buildProvisioningPayload(item),
      );
      setProvisioningResult(response);
      setItems((prev) =>
        prev.map((current) =>
          current.requestId === response.pilotRequest.requestId
            ? response.pilotRequest
            : current,
        ),
      );
    } catch (provisionError) {
      setError(
        provisionError instanceof Error
          ? provisionError.message
          : "Failed to approve and provision pilot request.",
      );
    } finally {
      setProvisioningId(null);
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
            <option value="approved_provisioning_failed">
              Approved Provisioning Failed
            </option>
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
                <Fragment key={item.requestId}>
                  <tr className="border-t border-lime-900/70 text-slate-100">
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
                        {item.status === "contacted" ? (
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedProvisioningId((current) =>
                                current === item.requestId
                                  ? null
                                  : item.requestId,
                              )
                            }
                            className="rounded-md border border-sky-500/40 bg-sky-950/35 px-2.5 py-1.5 text-xs font-semibold text-sky-100 transition hover:bg-sky-900/45"
                          >
                            {expandedProvisioningId === item.requestId
                              ? "Hide Provision Form"
                              : "Provision Pilot"}
                          </button>
                        ) : null}
                        {item.status === "contacted" ? (
                          <button
                            type="button"
                            disabled={
                              !canEdit || provisioningId === item.requestId
                            }
                            onClick={() => void onApproveAndProvision(item)}
                            className="rounded-md border border-emerald-500/40 bg-emerald-950/35 px-2.5 py-1.5 text-xs font-semibold text-emerald-100 transition enabled:hover:bg-emerald-900/45 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Approve + Provision
                          </button>
                        ) : null}
                        {item.status === "approved_provisioning_failed" ? (
                          <button
                            type="button"
                            disabled={
                              !canEdit || provisioningId === item.requestId
                            }
                            onClick={() => void onApproveAndProvision(item)}
                            className="rounded-md border border-amber-500/40 bg-amber-950/35 px-2.5 py-1.5 text-xs font-semibold text-amber-100 transition enabled:hover:bg-amber-900/45 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Retry Provisioning
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                  {expandedProvisioningId === item.requestId ? (
                    <tr className="border-t border-lime-900/70 bg-black/40">
                      <td colSpan={6} className="px-3 py-3">
                        <div className="grid gap-3 md:grid-cols-2">
                          <label className="grid gap-1 text-xs text-lime-100/90">
                            Course Name
                            <input
                              type="text"
                              value={getFormValues(item).courseName}
                              onChange={(event) =>
                                setCourseNameByRequestId((prev) => ({
                                  ...prev,
                                  [item.requestId]: event.target.value,
                                }))
                              }
                              className="rounded-md border border-lime-500/35 bg-black/55 px-2.5 py-2 text-sm text-lime-50 outline-none focus:border-lime-400"
                            />
                          </label>
                          <label className="grid gap-1 text-xs text-lime-100/90">
                            Course ID
                            <input
                              type="text"
                              value={getFormValues(item).courseId}
                              onChange={(event) =>
                                setCourseIdByRequestId((prev) => ({
                                  ...prev,
                                  [item.requestId]: event.target.value,
                                }))
                              }
                              className="rounded-md border border-lime-500/35 bg-black/55 px-2.5 py-2 text-sm text-lime-50 outline-none focus:border-lime-400"
                            />
                          </label>
                          <label className="grid gap-1 text-xs text-lime-100/90">
                            Instructor Email
                            <input
                              type="email"
                              value={getFormValues(item).instructorEmail}
                              onChange={(event) =>
                                setInstructorEmailByRequestId((prev) => ({
                                  ...prev,
                                  [item.requestId]: event.target.value,
                                }))
                              }
                              className="rounded-md border border-lime-500/35 bg-black/55 px-2.5 py-2 text-sm text-lime-50 outline-none focus:border-lime-400"
                            />
                          </label>
                          <label className="grid gap-1 text-xs text-lime-100/90">
                            Cohort Size
                            <input
                              type="number"
                              min={1}
                              step={1}
                              value={getFormValues(item).cohortSize}
                              onChange={(event) =>
                                setCohortSizeByRequestId((prev) => ({
                                  ...prev,
                                  [item.requestId]: event.target.value,
                                }))
                              }
                              className="rounded-md border border-lime-500/35 bg-black/55 px-2.5 py-2 text-sm text-lime-50 outline-none focus:border-lime-400"
                            />
                          </label>
                        </div>
                        <div className="mt-3 grid gap-3 md:grid-cols-[220px_minmax(0,1fr)]">
                          <label className="grid gap-1 text-xs text-lime-100/90">
                            Class Code Mode
                            <select
                              value={getFormValues(item).classCodeMode}
                              onChange={(event) =>
                                setClassCodeModeByRequestId((prev) => ({
                                  ...prev,
                                  [item.requestId]: event.target.value as
                                    | "auto"
                                    | "custom",
                                }))
                              }
                              className="rounded-md border border-lime-500/35 bg-black/55 px-2.5 py-2 text-sm text-lime-50 outline-none focus:border-lime-400"
                            >
                              <option value="auto">Auto-generate</option>
                              <option value="custom">Custom class code</option>
                            </select>
                          </label>
                          <label className="grid gap-1 text-xs text-lime-100/90">
                            Class Code
                            <input
                              type="text"
                              value={getFormValues(item).classCode}
                              onChange={(event) =>
                                setClassCodeByRequestId((prev) => ({
                                  ...prev,
                                  [item.requestId]: event.target.value,
                                }))
                              }
                              disabled={
                                getFormValues(item).classCodeMode !== "custom"
                              }
                              className="rounded-md border border-lime-500/35 bg-black/55 px-2.5 py-2 text-sm text-lime-50 outline-none focus:border-lime-400 disabled:cursor-not-allowed disabled:opacity-60"
                            />
                          </label>
                        </div>
                        <div className="mt-3 flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => void onManualProvision(item)}
                            disabled={manualProvisioningId === item.requestId}
                            className="rounded-md border border-emerald-500/40 bg-emerald-950/35 px-3 py-2 text-xs font-semibold text-emerald-100 transition enabled:hover:bg-emerald-900/45 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Provision Pilot
                          </button>
                          <p className="m-0 text-xs text-lime-100/75">
                            This provisions course + class code and stores
                            summary.
                          </p>
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {provisioningResult ? (
        <section className="rounded-xl border border-emerald-600/45 bg-emerald-950/25 p-4">
          <h2 className="m-0 text-base font-semibold text-emerald-200">
            Approve + Provision Result
          </h2>
          <p className="mb-2 mt-2 text-sm text-emerald-100/90">
            Request {provisioningResult.pilotRequest.requestId} is{" "}
            {provisioningResult.pilotRequest.status}.
          </p>
          <p className="mb-2 mt-0 text-sm text-emerald-100/90">
            Retry: {provisioningResult.isRetry ? "yes" : "no"} | Run:{" "}
            {provisioningResult.runCorrelationId}
          </p>
          <ul className="m-0 grid gap-1 pl-5 text-sm text-emerald-100/90">
            <li>
              Approve step: {provisioningResult.approvedStep ? "ok" : "failed"}
            </li>
            <li>
              Pilot provision step:{" "}
              {provisioningResult.pilotProvisionStep ? "ok" : "failed"}
            </li>
            {provisioningResult.pilotProvisionStep ? (
              <li>
                Class code: {provisioningResult.pilotProvisionStep.classCode} |
                Course: {provisioningResult.pilotProvisionStep.courseName}
              </li>
            ) : null}
            {provisioningResult.pilotProvisionStep?.provisionedBy ? (
              <li>
                Provisioned by:{" "}
                {provisioningResult.pilotProvisionStep.provisionedBy}
              </li>
            ) : null}
            {provisioningResult.pilotProvisionError ? (
              <li>
                Pilot provision error: {provisioningResult.pilotProvisionError}
              </li>
            ) : null}
            <li>
              Instructor provision step:{" "}
              {provisioningResult.instructorProvisionStep ? "ok" : "failed"}
            </li>
            {provisioningResult.instructorProvisionStep ? (
              <li>
                Instructor group assigned:{" "}
                {provisioningResult.instructorProvisionStep.groupAssigned
                  ? "yes"
                  : "no"}
              </li>
            ) : null}
            {provisioningResult.instructorProvisionStep?.instructorUserId ? (
              <li>
                Instructor user id:{" "}
                {provisioningResult.instructorProvisionStep.instructorUserId}
              </li>
            ) : null}
            {provisioningResult.instructorProvisionError ? (
              <li>
                Instructor provision error:{" "}
                {provisioningResult.instructorProvisionError}
              </li>
            ) : null}
          </ul>
        </section>
      ) : null}

      {manualProvisioningResult ? (
        <section className="rounded-xl border border-sky-600/45 bg-sky-950/25 p-4">
          <h2 className="m-0 text-base font-semibold text-sky-200">
            Provisioning Summary
          </h2>
          <p className="mb-2 mt-2 text-sm text-sky-100/90">
            Request{" "}
            {manualProvisioningResult.provisioningSummary.pilotRequestId}
          </p>
          <p className="m-0 text-sm text-sky-100/90">
            Class code: {manualProvisioningResult.provisioningSummary.classCode}{" "}
            | Course: {manualProvisioningResult.provisioningSummary.courseName}
          </p>
        </section>
      ) : null}
    </div>
  );
}
