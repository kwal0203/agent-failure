import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";
import {
  sessionMetadataQueryKey,
  useSessionMetadataQuery,
} from "../../../query/sessionMetadata";
import {
  sessionTraceQueryKey,
  useSessionTraceQuery,
} from "../../../query/sessionTrace";
import { mapPersistedTraceToTelemetryLogs } from "../telemetry";
import type {
  LearnerFeedbackItem,
  SessionInvoice,
  SessionMetadata,
  SessionProgressChip,
  SessionTelemetryLog,
  TimelineEvent,
} from "../types";

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
  const timelineEvents = traceQuery.data?.timelineEvents ?? [];

  const telemetryLogs = useMemo(
    () => mapPersistedTraceToTelemetryLogs(traceQuery.data?.events ?? []),
    [traceQuery.data],
  );

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
