import type { SessionTelemetryLog, SessionTraceEvent } from "./types";

function stringPayload(
  payload: Record<string, unknown>,
  key: string,
): string | null {
  const value = payload[key];
  return typeof value === "string" && value.trim() ? value : null;
}

export function mapPersistedTraceToTelemetryLogs(
  events: SessionTraceEvent[],
): SessionTelemetryLog[] {
  const logsById = new Map<string, SessionTelemetryLog>();

  for (const event of events) {
    const payload = event.payload ?? {};

    if (
      event.event_type === "SIMULATED_TELEMETRY_SIGNAL" &&
      payload.simulated === true
    ) {
      const signalId = stringPayload(payload, "signal_id");
      const section = stringPayload(payload, "section");
      const severity = stringPayload(payload, "severity");
      const message = stringPayload(payload, "message");
      if (!signalId || !section || !severity || !message) continue;

      const id = `simulated-telemetry-${signalId}`;
      if (!logsById.has(id)) {
        logsById.set(id, {
          id,
          created_at: event.occurred_at,
          log_case: signalId,
          message: `${severity.toUpperCase()}: ${message} (runbook section ${section})`,
          simulated: true,
        });
      }
      continue;
    }

    const isMissingRecoveryArtifact =
      event.event_type === "TOOL_CALL_FAILED" &&
      payload.tool_name === "read_file" &&
      payload.error_code === "FILE_NOT_FOUND" &&
      payload.qualifying_log === true &&
      payload.log_case === "missing_recovery_artifact";
    if (!isMissingRecoveryArtifact) continue;

    const targetResource =
      stringPayload(payload, "target_resource") ?? "unknown resource";
    const id = `trace-log-${event.id}`;
    logsById.set(id, {
      id,
      created_at: event.occurred_at,
      log_case: "missing_recovery_artifact",
      message: `ERROR: Recovery artifact missing (${targetResource})`,
      simulated: true,
    });
  }

  return [...logsById.values()]
    .sort((a, b) => {
      const timestampDifference =
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      return timestampDifference !== 0
        ? timestampDifference
        : a.id.localeCompare(b.id);
    })
    .slice(-10);
}
