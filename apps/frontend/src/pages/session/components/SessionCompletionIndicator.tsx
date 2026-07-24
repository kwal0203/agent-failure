import { formatTime, type StatusTone, statusChipClassName } from "../helpers";
import type { SessionCompletionStatus } from "../types";

type SessionCompletionIndicatorProps = {
  completionStatus: SessionCompletionStatus;
  completedAt: string | null;
  completionReasonCode: string | null;
};

function completionTone(status: SessionCompletionStatus): StatusTone {
  switch (status) {
    case "completed_success":
      return "success";
    case "completed_failure":
      return "danger";
    default:
      return "info";
  }
}

function completionLabel(status: SessionCompletionStatus): string {
  switch (status) {
    case "completed_success":
      return "Outcome: completed_success";
    case "completed_failure":
      return "Outcome: completed_failure";
    default:
      return "Outcome: in_progress";
  }
}

function completionDetails(
  status: SessionCompletionStatus,
  completedAt: string | null,
  completionReasonCode: string | null,
): string | null {
  const fragments: string[] = [];
  if (completedAt) {
    fragments.push(`Completed at ${formatTime(completedAt)}`);
  }
  if (completionReasonCode) {
    fragments.push(`Reason ${completionReasonCode}`);
  }
  if (status === "completed_failure" && fragments.length === 0) {
    return "Failure handling UX placeholder.";
  }
  if (fragments.length === 0) {
    return null;
  }
  return fragments.join(" • ");
}

export function SessionCompletionIndicator({
  completionStatus,
  completedAt,
  completionReasonCode,
}: SessionCompletionIndicatorProps) {
  const details = completionDetails(
    completionStatus,
    completedAt,
    completionReasonCode,
  );

  return (
    <div
      className={statusChipClassName(
        completionTone(completionStatus),
        "flex items-center gap-2",
      )}
    >
      <strong>{completionLabel(completionStatus)}</strong>
      {details ? (
        <span className="whitespace-nowrap text-xs opacity-90">{details}</span>
      ) : null}
    </div>
  );
}
