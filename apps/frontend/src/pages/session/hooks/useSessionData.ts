import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  SESSION_METADATA_POLL_BASE_MS,
  SESSION_METADATA_POLL_JITTER_RATIO,
} from "../constants";
import { jitterDelayMs } from "../helpers";
import { mapPersistedTraceToTimelineEvent } from "../timelineEventMapper";
import type {
  GetSessionMetadataResponse,
  GetSessionTraceResponse,
  LearnerFeedbackItem,
  SessionInvoice,
  SessionMetadata,
  SessionProgressChip,
  SessionTelemetryLog,
  TimelineEvent,
} from "../types";
import { API_BASE, getAuthHeader } from "../ui";

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
  setMetadata: Dispatch<SetStateAction<SessionMetadata | null>>;
  progressReady: boolean;
  timelineEvents: TimelineEvent[];
  feedbackError: string | null;
  feedbackLoading: boolean;
  feedbackReady: boolean;
  appendTimelineEvent: (event: TimelineEvent) => void;
  registerLearnerFeedbackEvents: (
    feedback: LearnerFeedbackItem[],
    timestamp: string,
  ) => void;
  refreshSessionMetadata: () => Promise<void>;
  sessionState: string;
  progressChips: SessionProgressChip[];
  telemetryLogs: SessionTelemetryLog[];
  invoices: SessionInvoice[];
};

export function useSessionData({
  sessionId,
}: UseSessionDataParams): UseSessionDataResult {
  const [metadata, setMetadata] = useState<SessionMetadata | null>(null);
  const [metadataReady, setMetadataReady] = useState(false);
  const seenTimelineEventIdsRef = useRef(new Set<string>());
  const seenTelemetryLogIdsRef = useRef(new Set<string>());
  const seenInvoiceIdsRef = useRef(new Set<string>());
  const lab2TelemetryCursorRef = useRef(0);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [telemetryLogs, setTelemetryLogs] = useState<SessionTelemetryLog[]>([]);
  const [invoices, setInvoices] = useState<SessionInvoice[]>([]);

  const appendTelemetryLog = useCallback((log: SessionTelemetryLog) => {
    if (seenTelemetryLogIdsRef.current.has(log.id)) {
      return;
    }
    seenTelemetryLogIdsRef.current.add(log.id);
    setTelemetryLogs((prev) => {
      const next = [...prev, log];
      next.sort((a, b) => {
        const tsDiff =
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        if (tsDiff !== 0) {
          return tsDiff;
        }
        return a.id.localeCompare(b.id);
      });
      return next.slice(-10);
    });
  }, []);

  const appendTimelineEvent = useCallback((event: TimelineEvent) => {
    if (seenTimelineEventIdsRef.current.has(event.id)) {
      return;
    }
    seenTimelineEventIdsRef.current.add(event.id);
    setTimelineEvents((prev) => [...prev, event]);
  }, []);

  const appendInvoice = useCallback((invoice: SessionInvoice) => {
    if (seenInvoiceIdsRef.current.has(invoice.id)) {
      return;
    }
    seenInvoiceIdsRef.current.add(invoice.id);
    setInvoices((prev) => {
      const next = [...prev, invoice];
      next.sort((a, b) => {
        const tsDiff =
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        if (tsDiff !== 0) {
          return tsDiff;
        }
        return a.id.localeCompare(b.id);
      });
      return next.slice(-10);
    });
  }, []);

  const markInvoiceHandled = useCallback(
    (
      invoiceId: string,
      options: {
        handledBy: string;
        handledAt: string;
        vendorName?: string;
        amount?: number;
      },
    ) => {
      const { handledBy, handledAt, vendorName, amount } = options;
      const normalizedInvoiceId = invoiceId.trim();
      if (!normalizedInvoiceId) {
        return;
      }

      setInvoices((prev) => {
        let found = false;
        const next = prev.map((invoice) => {
          if (invoice.invoice_id !== normalizedInvoiceId) {
            return invoice;
          }
          found = true;
          return {
            ...invoice,
            handled_by: handledBy,
            handled_at: handledAt,
          };
        });

        if (found) {
          return next;
        }

        const fallbackId = `trace-invoice-${normalizedInvoiceId}`;
        if (!seenInvoiceIdsRef.current.has(fallbackId)) {
          seenInvoiceIdsRef.current.add(fallbackId);
        }
        return [
          ...next,
          {
            id: fallbackId,
            invoice_id: normalizedInvoiceId,
            vendor_name: vendorName ?? "Unknown vendor",
            amount: amount ?? 0,
            currency: "USD",
            created_at: handledAt,
            handled_by: handledBy,
            handled_at: handledAt,
          },
        ];
      });
    },
    [],
  );

  const refreshTraceTimeline = useCallback(async () => {
    if (!sessionId) return;

    try {
      const res = await fetch(
        `${API_BASE}/api/v1/sessions/${sessionId}/trace`,
        {
          method: "GET",
          headers: {
            Authorization: getAuthHeader(),
            "Content-Type": "application/json",
          },
        },
      );
      if (!res.ok) {
        return;
      }

      const data = (await res.json()) as GetSessionTraceResponse;
      const events = Array.isArray(data.events) ? data.events : [];
      for (const event of events) {
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
          appendTelemetryLog({
            id: `trace-log-${event.id}`,
            created_at: event.occurred_at,
            log_case: "missing_recovery_artifact",
            message: `ERROR: Recovery artifact missing (${targetResource})`,
          });
        }
        const isQualifyingLab3InvoiceFeed =
          event.event_type === "TOOL_CALL_SUCCEEDED" &&
          payload.tool_name === "read_invoice" &&
          payload.qualifying_log === true &&
          payload.log_case === "incoming_invoice_feed";
        if (isQualifyingLab3InvoiceFeed) {
          const payloadInvoiceId =
            typeof payload.invoice_id === "string" ? payload.invoice_id : null;
          const payloadVendorName =
            typeof payload.vendor_name === "string"
              ? payload.vendor_name
              : null;
          const payloadAmount =
            typeof payload.amount === "number" ? payload.amount : null;
          if (payloadInvoiceId && payloadVendorName && payloadAmount !== null) {
            appendInvoice({
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
        const timelineEvent = mapPersistedTraceToTimelineEvent(event);
        if (timelineEvent) {
          appendTimelineEvent(timelineEvent);
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
          markInvoiceHandled(payloadInvoiceId, {
            handledBy,
            handledAt: event.occurred_at,
            vendorName: payloadVendorName ?? undefined,
            amount: payloadAmount ?? undefined,
          });
        }
      }
    } catch {
      return;
    }
  }, [
    appendInvoice,
    appendTelemetryLog,
    appendTimelineEvent,
    markInvoiceHandled,
    sessionId,
  ]);

  const refreshSessionMetadata = useCallback(async () => {
    if (!sessionId) return;

    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}`, {
        method: "GET",
        headers: {
          Authorization: getAuthHeader(),
          "Content-Type": "application/json",
        },
      });

      if (!res.ok) {
        return;
      }

      const data = (await res.json()) as GetSessionMetadataResponse;
      const session = data.session;
      setMetadata(session);
      setMetadataReady(true);
    } catch {
      return;
    }
  }, [sessionId]);

  const registerLearnerFeedbackEvents = useCallback(() => {
    // Persisted session metadata is the source of truth for rendered feedback.
    // When websocket feedback arrives, refresh immediately so UI updates even
    // if background polling is paused (for example outside ACTIVE/PROVISIONING).
    void refreshSessionMetadata();
    void refreshTraceTimeline();
  }, [refreshSessionMetadata, refreshTraceTimeline]);

  const progressChips = metadata?.progress_chips ?? [];
  const progressReady = metadataReady;
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
      appendTelemetryLog({
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
  }, [appendTelemetryLog, metadata?.lab_id, metadata?.state, sessionId]);

  // Poll persisted metadata + trace so timeline stays sourced from durable annotated
  // trace events instead of websocket-only transient events.
  useEffect(() => {
    if (!sessionId) return;
    const state = (metadata?.state ?? "").toUpperCase();
    if (
      state &&
      !["CREATED", "PROVISIONING", "ACTIVE", "IDLE"].includes(state)
    ) {
      return;
    }

    let cancelled = false;
    let timeoutId: number | null = null;

    const tick = async () => {
      if (cancelled) return;
      await refreshSessionMetadata();
      await refreshTraceTimeline();
      if (cancelled) return;
      timeoutId = window.setTimeout(
        tick,
        jitterDelayMs(
          SESSION_METADATA_POLL_BASE_MS,
          SESSION_METADATA_POLL_JITTER_RATIO,
        ),
      );
    };

    void tick();

    return () => {
      cancelled = true; // Guard for in-flight work
      if (timeoutId !== null) window.clearTimeout(timeoutId); // This stops the polling
    };
  }, [
    sessionId,
    metadata?.state,
    refreshSessionMetadata,
    refreshTraceTimeline,
  ]);

  return {
    metadata,
    setMetadata,
    progressReady,
    timelineEvents,
    feedbackError: null,
    feedbackLoading: false,
    feedbackReady: metadataReady,
    appendTimelineEvent,
    registerLearnerFeedbackEvents,
    refreshSessionMetadata,
    sessionState,
    progressChips,
    telemetryLogs,
    invoices,
  };
}
