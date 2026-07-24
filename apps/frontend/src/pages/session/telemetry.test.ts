import { describe, expect, it } from "vitest";
import { mapPersistedTraceToTelemetryLogs } from "./telemetry";
import type { SessionTraceEvent } from "./types";

function traceEvent(
  overrides: Partial<SessionTraceEvent> & Pick<SessionTraceEvent, "id">,
): SessionTraceEvent {
  return {
    id: overrides.id,
    event_index: overrides.event_index ?? 0,
    family: overrides.family ?? "runtime",
    event_type: overrides.event_type ?? "SIMULATED_TELEMETRY_SIGNAL",
    source: overrides.source ?? "session_stream_service",
    occurred_at: overrides.occurred_at ?? "2026-07-24T12:00:00.000Z",
    payload: overrides.payload ?? {},
    report_selectable: overrides.report_selectable ?? false,
    evidence_type: overrides.evidence_type ?? "noise",
    default_priority: overrides.default_priority ?? "low",
    objective_keys: overrides.objective_keys,
    why_it_matters: overrides.why_it_matters,
  };
}

describe("persisted session telemetry", () => {
  it("hydrates, orders, and deduplicates simulated signals by stable ID", () => {
    const events = [
      traceEvent({
        id: "event-b",
        event_index: 2,
        occurred_at: "2026-07-24T12:00:00.002Z",
        payload: {
          signal_id: "lab2.queue-backlog-growth.v1",
          section: "D",
          severity: "error",
          message: "Queue backlog growth detected",
          simulated: true,
        },
      }),
      traceEvent({
        id: "event-a",
        event_index: 1,
        occurred_at: "2026-07-24T12:00:00.001Z",
        payload: {
          signal_id: "lab2.auth-retry-surge.v1",
          section: "B",
          severity: "error",
          message: "Auth retry surge detected",
          simulated: true,
        },
      }),
      traceEvent({
        id: "event-a-duplicate",
        event_index: 3,
        occurred_at: "2026-07-24T12:00:01.000Z",
        payload: {
          signal_id: "lab2.auth-retry-surge.v1",
          section: "B",
          severity: "error",
          message: "Auth retry surge detected",
          simulated: true,
        },
      }),
    ];

    expect(mapPersistedTraceToTelemetryLogs(events)).toEqual([
      {
        id: "simulated-telemetry-lab2.auth-retry-surge.v1",
        created_at: "2026-07-24T12:00:00.001Z",
        log_case: "lab2.auth-retry-surge.v1",
        message: "ERROR: Auth retry surge detected (runbook section B)",
        simulated: true,
      },
      {
        id: "simulated-telemetry-lab2.queue-backlog-growth.v1",
        created_at: "2026-07-24T12:00:00.002Z",
        log_case: "lab2.queue-backlog-growth.v1",
        message: "ERROR: Queue backlog growth detected (runbook section D)",
        simulated: true,
      },
    ]);
  });

  it("keeps qualifying trace-backed recovery failures", () => {
    const events = [
      traceEvent({
        id: "tool-failure",
        family: "tool",
        event_type: "TOOL_CALL_FAILED",
        payload: {
          tool_name: "read_file",
          target_resource: "/var/recovery/missing.log",
          error_code: "FILE_NOT_FOUND",
          qualifying_log: true,
          log_case: "missing_recovery_artifact",
        },
      }),
    ];

    expect(mapPersistedTraceToTelemetryLogs(events)).toEqual([
      {
        id: "trace-log-tool-failure",
        created_at: "2026-07-24T12:00:00.000Z",
        log_case: "missing_recovery_artifact",
        message: "ERROR: Recovery artifact missing (/var/recovery/missing.log)",
        simulated: true,
      },
    ]);
  });

  it("ignores malformed or non-simulated scenario signals", () => {
    const events = [
      traceEvent({
        id: "not-simulated",
        payload: {
          signal_id: "lab2.signal.v1",
          section: "A",
          severity: "error",
          message: "Signal",
          simulated: false,
        },
      }),
      traceEvent({
        id: "missing-identifier",
        payload: {
          section: "A",
          severity: "error",
          message: "Signal",
          simulated: true,
        },
      }),
    ];

    expect(mapPersistedTraceToTelemetryLogs(events)).toEqual([]);
  });
});
