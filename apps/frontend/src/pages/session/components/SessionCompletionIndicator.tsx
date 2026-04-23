import { formatTime, statusChipStyle } from "../helpers";
import type { SessionCompletionStatus } from "../types";

type SessionCompletionIndicatorProps = {
  completionStatus: SessionCompletionStatus;
  completedAt: string | null;
  completionReasonCode: string | null;
};

function completionTone(status: SessionCompletionStatus): {
  background: string;
  border: string;
  color: string;
} {
  switch (status) {
    case "completed_success":
      return {
        background: "rgba(10, 50, 33, 0.72)",
        border: "1px solid #2e7b57",
        color: "#b9ffe0",
      };
    case "completed_failure":
      return {
        background: "rgba(70, 19, 37, 0.72)",
        border: "1px solid #8b3252",
        color: "#ffd1df",
      };
    default:
      return {
        background: "rgba(8, 31, 50, 0.72)",
        border: "1px solid #285272",
        color: "#9fe4fb",
      };
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
      style={{
        ...statusChipStyle(completionTone(completionStatus)),
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}
    >
      <strong>{completionLabel(completionStatus)}</strong>
      {details ? (
        <span style={{ fontSize: 12, opacity: 0.92, whiteSpace: "nowrap" }}>
          {details}
        </span>
      ) : null}
    </div>
  );
}
