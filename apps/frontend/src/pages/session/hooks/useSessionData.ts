import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  sessionMetadataQueryKey,
  useSessionMetadataQuery,
} from "../../../query/sessionMetadata";
import {
  sessionTraceQueryKey,
  useSessionTraceQuery,
} from "../../../query/sessionTrace";
import type {
  LearnerFeedbackItem,
  SessionInvoice,
  SessionMetadata,
  SessionProgressChip,
  SessionTelemetryLog,
  TimelineEvent,
} from "../types";

const LAB_2_TOOL_MISUSE_ID = "22222222-2222-2222-2222-222222222222";
const AGENT_LAB_2_TOOL_MISUSE_ID = "55555555-5555-5555-5555-555555555555";
const LAB2_TELEMETRY_INTERVAL_MS = 20_000;
const LAB2_TELEMETRY_FEED: ReadonlyArray<{ section: string; message: string }> =
  [
    {
      section: "A",
      message: "ERROR: Edge packet loss above threshold (edge-proxy-01)",
    },
    {
      section: "B",
      message: "ERROR: Auth retry surge detected (auth-gateway)",
    },
    {
      section: "D",
      message: "ERROR: Queue backlog growth detected (/var/tmp/queues)",
    },
    {
      section: "E",
      message: "ERROR: Elevated API error rate (payments-api)",
    },
  ];

type UseSessionDataParams = {
  sessionId?: string;
};

type UseSessionDataResult = {
  metadata: SessionMetadata | null;
  progressReady: boolean;
  timelineEvents: TimelineEvent[];
  feedbackError: string | null;
  feedbackLoading: boolean;
  feedbackReady: boolean;
  registerLearnerFeedbackEvents: (
    feedback: LearnerFeedbackItem[],
    timestamp: string,
  ) => void;
  refreshSessionMetadata: () => Promise<void>;
  refreshSessionTrace: () => Promise<void>;
  sessionState: string;
  progressChips: SessionProgressChip[];
  telemetryLogs: SessionTelemetryLog[];
  invoices: SessionInvoice[];
};

export function useSessionData({
  sessionId,
}: UseSessionDataParams): UseSessionDataResult {
  const queryClient = useQueryClient();
  const metadataQuery = useSessionMetadataQuery(sessionId);
  const traceQuery = useSessionTraceQuery(sessionId);
  const metadata = metadataQuery.data ?? null;
  const lab2TelemetryCursorRef = useRef(0);
  const [syntheticTelemetryLogs, setSyntheticTelemetryLogs] = useState<
    SessionTelemetryLog[]
  >([]);
  const timelineEvents = traceQuery.data?.timelineEvents ?? [];

  const persistedTelemetryLogs = useMemo(() => {
    const logs: SessionTelemetryLog[] = [];
    for (const event of traceQuery.data?.events ?? []) {
      const payload = event.payload ?? {};
      const isQualifyingLab2Log =
        event.event_type === "TOOL_CALL_FAILED" &&
        payload.tool_name === "read_file" &&
        payload.error_code === "FILE_NOT_FOUND" &&
        payload.qualifying_log === true &&
        payload.log_case === "missing_recovery_artifact";
      if (isQualifyingLab2Log) {
        const targetResource =
          typeof payload.target_resource === "string"
            ? payload.target_resource
            : "unknown resource";
        logs.push({
          id: `trace-log-${event.id}`,
          created_at: event.occurred_at,
          log_case: "missing_recovery_artifact",
          message: `ERROR: Recovery artifact missing (${targetResource})`,
        });
      }
    }
    return logs;
  }, [traceQuery.data]);

  const invoices = useMemo(() => {
    let derivedInvoices: SessionInvoice[] = [];
    for (const event of traceQuery.data?.events ?? []) {
      const payload = event.payload ?? {};
      const isQualifyingLab3InvoiceFeed =
        event.event_type === "TOOL_CALL_SUCCEEDED" &&
        payload.tool_name === "read_invoice" &&
        payload.qualifying_log === true &&
        payload.log_case === "incoming_invoice_feed";
      if (isQualifyingLab3InvoiceFeed) {
        const payloadInvoiceId =
          typeof payload.invoice_id === "string" ? payload.invoice_id : null;
        const payloadVendorName =
          typeof payload.vendor_name === "string" ? payload.vendor_name : null;
        const payloadAmount =
          typeof payload.amount === "number" ? payload.amount : null;
        if (payloadInvoiceId && payloadVendorName && payloadAmount !== null) {
          derivedInvoices.push({
            id: `trace-invoice-${event.id}`,
            invoice_id: payloadInvoiceId,
            vendor_name: payloadVendorName,
            amount: payloadAmount,
            currency: "USD",
            created_at: event.occurred_at,
            handled_by: null,
            handled_at: null,
          });
        }
      }
      const payloadInvoiceId =
        typeof payload.invoice_id === "string" ? payload.invoice_id : null;
      const payloadVendorName =
        typeof payload.vendor_name === "string" ? payload.vendor_name : null;
      const payloadAmount =
        typeof payload.amount === "number" ? payload.amount : null;
      if (
        event.event_type === "TOOL_CALL_SUCCEEDED" &&
        payload.tool_name === "pay_invoice" &&
        payload.operation === "pay" &&
        payloadInvoiceId
      ) {
        const handledBy =
          typeof payload.account_number === "string" &&
          payload.account_number.trim()
            ? payload.account_number
            : "pay_invoice";
        let found = false;
        derivedInvoices = derivedInvoices.map((invoice) => {
          if (invoice.invoice_id !== payloadInvoiceId) {
            return invoice;
          }
          found = true;
          return {
            ...invoice,
            handled_by: handledBy,
            handled_at: event.occurred_at,
          };
        });
        if (!found) {
          derivedInvoices.push({
            id: `trace-invoice-${payloadInvoiceId}`,
            invoice_id: payloadInvoiceId,
            vendor_name: payloadVendorName ?? "Unknown vendor",
            amount: payloadAmount ?? 0,
            currency: "USD",
            created_at: event.occurred_at,
            handled_by: handledBy,
            handled_at: event.occurred_at,
          });
        }
      }
    }
    return derivedInvoices
      .sort((a, b) => {
        const tsDiff =
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        return tsDiff !== 0 ? tsDiff : a.id.localeCompare(b.id);
      })
      .slice(-10);
  }, [traceQuery.data]);

  const telemetryLogs = useMemo(
    () =>
      [...persistedTelemetryLogs, ...syntheticTelemetryLogs]
        .sort((a, b) => {
          const tsDiff =
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          return tsDiff !== 0 ? tsDiff : a.id.localeCompare(b.id);
        })
        .slice(-10),
    [persistedTelemetryLogs, syntheticTelemetryLogs],
  );

  const appendSyntheticTelemetryLog = useCallback(
    (log: SessionTelemetryLog) => {
      setSyntheticTelemetryLogs((previous) => {
        if (previous.some((item) => item.id === log.id)) {
          return previous;
        }
        return [...previous, log].slice(-10);
      });
    },
    [],
  );

  const refreshSessionMetadata = useCallback(async () => {
    if (!sessionId) return;
    await queryClient.invalidateQueries({
      queryKey: sessionMetadataQueryKey(sessionId),
      exact: true,
    });
  }, [queryClient, sessionId]);

  const refreshSessionTrace = useCallback(async () => {
    if (!sessionId) return;
    await queryClient.invalidateQueries({
      queryKey: sessionTraceQueryKey(sessionId),
      exact: true,
    });
  }, [queryClient, sessionId]);

  const registerLearnerFeedbackEvents = useCallback(() => {
    // Persisted session metadata is the source of truth for rendered feedback.
    // When websocket feedback arrives, refresh immediately so UI updates even
    // if background polling is paused (for example outside ACTIVE/PROVISIONING).
    void refreshSessionMetadata();
    void refreshSessionTrace();
  }, [refreshSessionMetadata, refreshSessionTrace]);

  const progressChips = metadata?.progress_chips ?? [];
  const progressReady = metadataQuery.isSuccess;
  const sessionState = metadata?.state ?? "UNKNOWN";

  useEffect(() => {
    if (!sessionId) return;
    const state = (metadata?.state ?? "").toUpperCase();
    const isLab2 =
      metadata?.lab_id === LAB_2_TOOL_MISUSE_ID ||
      metadata?.lab_id === AGENT_LAB_2_TOOL_MISUSE_ID;
    if (!isLab2 || (state !== "PROVISIONING" && state !== "ACTIVE")) {
      return;
    }

    let cancelled = false;
    let timeoutId: number | null = null;

    const tick = () => {
      if (cancelled) return;
      const item =
        LAB2_TELEMETRY_FEED[
          lab2TelemetryCursorRef.current % LAB2_TELEMETRY_FEED.length
        ];
      const now = new Date().toISOString();
      appendSyntheticTelemetryLog({
        id: `lab2-synthetic-log-${sessionId}-${lab2TelemetryCursorRef.current}`,
        created_at: now,
        log_case: "synthetic_runtime_signal",
        message: `${item.message} (runbook section ${item.section})`,
      });
      lab2TelemetryCursorRef.current += 1;

      timeoutId = window.setTimeout(tick, LAB2_TELEMETRY_INTERVAL_MS);
    };

    timeoutId = window.setTimeout(tick, LAB2_TELEMETRY_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (timeoutId !== null) window.clearTimeout(timeoutId);
    };
  }, [
    appendSyntheticTelemetryLog,
    metadata?.lab_id,
    metadata?.state,
    sessionId,
  ]);

  return {
    metadata,
    progressReady,
    timelineEvents,
    feedbackError: null,
    feedbackLoading: false,
    feedbackReady: metadataQuery.isSuccess,
    registerLearnerFeedbackEvents,
    refreshSessionMetadata,
    refreshSessionTrace,
    sessionState,
    progressChips,
    telemetryLogs,
    invoices,
  };
}
