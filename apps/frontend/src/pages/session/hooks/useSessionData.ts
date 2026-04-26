import type { Dispatch, SetStateAction } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  SESSION_METADATA_POLL_BASE_MS,
  SESSION_METADATA_POLL_JITTER_RATIO,
} from "../constants";
import { jitterDelayMs } from "../helpers";
import type {
  GetSessionMetadataResponse,
  GetSessionTraceResponse,
  LearnerFeedbackItem,
  SessionFeedbackItem,
  SessionInvoice,
  SessionMetadata,
  SessionProgressChip,
  SessionTelemetryLog,
  SessionTraceEvent,
  TimelineEvent,
} from "../types";
import { API_BASE, AUTH_HEADER, humanizeFeedbackKey } from "../ui";

const LAB_2_TOOL_MISUSE_ID = "22222222-2222-2222-2222-222222222222";
const LAB_3_MEMORY_POISONING_ID = "33333333-3333-3333-3333-333333333333";
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
const LAB3_INVOICE_INTERVAL_MS = 20_000;
const LAB3_INVOICE_SEED: ReadonlyArray<{
  invoice_id: string;
  vendor_name: string;
  amount: number;
  currency: string;
}> = [];
const LAB3_COMPANY_PREFIXES: ReadonlyArray<string> = [
  "Apex",
  "Beacon",
  "Cobalt",
  "Delta",
  "Evergreen",
  "Falcon",
  "Granite",
  "Harbor",
  "Ironwood",
  "Juniper",
];
const LAB3_COMPANY_SUFFIXES: ReadonlyArray<string> = [
  "Analytics",
  "Bioworks",
  "Capital",
  "Dynamics",
  "Enterprises",
  "Fabrication",
  "Group",
  "Holdings",
  "Logistics",
  "Systems",
];
const LAB3_FAKE_COMPANIES: ReadonlyArray<{
  slug: string;
  vendor_name: string;
  base_amount: number;
  currency: string;
}> = LAB3_COMPANY_PREFIXES.flatMap((prefix, prefixIndex) =>
  LAB3_COMPANY_SUFFIXES.map((suffix, suffixIndex) => {
    const vendorName = `${prefix} ${suffix}`;
    const slug = vendorName.toLowerCase().replace(/\s+/g, "-");
    const listIndex = prefixIndex * LAB3_COMPANY_SUFFIXES.length + suffixIndex;
    return {
      slug,
      vendor_name: vendorName,
      base_amount: 7400 + listIndex * 185.4,
      currency: "USD",
    };
  }),
);

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

function formatPersistedTraceTitle(event: SessionTraceEvent): string {
  const toolName = event.payload.tool_name;
  const normalizedToolName =
    typeof toolName === "string" ? toolName.trim() : "";
  const humanizedToolName = normalizedToolName
    ? normalizedToolName
        .split("_")
        .filter((part) => part.length > 0)
        .map((part, idx) =>
          idx === 0
            ? part.charAt(0).toUpperCase() + part.slice(1)
            : part.toLowerCase(),
        )
        .join(" ")
    : "";
  if (
    event.event_type === "TOOL_CALL_SUCCEEDED" &&
    toolName === "write_memory"
  ) {
    return "Memory write accepted";
  }
  if (
    event.event_type === "TOOL_CALL_SUCCEEDED" &&
    toolName === "retrieve_memory"
  ) {
    return "Payment memory retrieved";
  }
  if (
    event.event_type === "TOOL_CALL_SUCCEEDED" &&
    toolName === "pay_invoice"
  ) {
    return "Invoice payment routed";
  }
  if (
    event.event_type === "TOOL_CALL_REQUESTED" &&
    toolName === "pay_invoice"
  ) {
    return "Invoice payment requested";
  }
  if (event.event_type === "TOOL_CALL_FAILED" && toolName === "pay_invoice") {
    return "Invoice payment failed";
  }
  if (event.event_type === "TOOL_CALL_REQUESTED" && humanizedToolName) {
    return `${humanizedToolName} requested`;
  }
  if (event.event_type === "TOOL_CALL_SUCCEEDED" && humanizedToolName) {
    return `${humanizedToolName} succeeded`;
  }
  if (event.event_type === "TOOL_CALL_FAILED" && humanizedToolName) {
    return `${humanizedToolName} failed`;
  }
  return event.event_type
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function mapPersistedTraceToTimelineEvent(
  event: SessionTraceEvent,
): TimelineEvent | null {
  const timestamp = event.occurred_at;
  const eventId = `trace-${event.id}`;
  if (event.event_type === "SESSION_CREATED") {
    return {
      id: eventId,
      timestamp,
      type: "system",
      granularity: "high",
      title: "Session created",
      description: "Lab session was created.",
    };
  }

  if (event.event_type === "MODEL_TURN_COMPLETED") {
    return {
      id: eventId,
      timestamp,
      type: "agent_action",
      granularity: "high",
      title: "Agent response completed",
      description: "Assistant completed a response turn.",
    };
  }

  if (event.event_type === "MODEL_TURN_FAILED") {
    const errorCode =
      typeof event.payload.error_code === "string"
        ? event.payload.error_code
        : "UNKNOWN";
    return {
      id: eventId,
      timestamp,
      type: "system",
      granularity: "high",
      title: "Agent response failed",
      description: `Model turn failed (${errorCode}).`,
      important: true,
    };
  }

  if (event.event_type === "ATTACK_EMAIL_SENT") {
    const subject =
      typeof event.payload.subject === "string" ? event.payload.subject : "";
    const emailFrom =
      typeof event.payload.email_from === "string"
        ? event.payload.email_from
        : "";
    const emailId =
      typeof event.payload.email_id === "string" && event.payload.email_id
        ? ` (id: ${event.payload.email_id})`
        : "";
    return {
      id: eventId,
      timestamp,
      type: "attacker_action",
      granularity: "high",
      title: "Email injected to inbox",
      description: `Email accepted${emailId}.`,
      details: `From: ${emailFrom}\nSubject: ${subject}`,
    };
  }

  if (event.event_type === "RUNTIME_PROVISION_REQUESTED") {
    return {
      id: eventId,
      timestamp,
      type: "system",
      granularity: "high",
      title: "Runtime provisioning requested",
      description: "Control plane requested runtime provisioning.",
    };
  }

  if (event.event_type === "RUNTIME_PROVISION_ACCEPTED") {
    return {
      id: eventId,
      timestamp,
      type: "system",
      granularity: "high",
      title: "Runtime provisioning accepted",
      description: "Runtime was provisioned and accepted.",
    };
  }

  if (event.event_type === "RUNTIME_PROVISION_FAILED") {
    const reasonCode =
      typeof event.payload.reason_code === "string"
        ? event.payload.reason_code
        : "UNKNOWN";
    return {
      id: eventId,
      timestamp,
      type: "system",
      granularity: "high",
      title: "Runtime provisioning failed",
      description: `Runtime provisioning failed (${reasonCode}).`,
      important: true,
    };
  }

  if (
    event.event_type === "TOOL_CALL_REQUESTED" ||
    event.event_type === "TOOL_CALL_SUCCEEDED" ||
    event.event_type === "TOOL_CALL_FAILED"
  ) {
    const toolName =
      typeof event.payload.tool_name === "string"
        ? event.payload.tool_name
        : "";
    const statusWord = event.event_type
      .replace("TOOL_CALL_", "")
      .toLowerCase()
      .replaceAll("_", " ");
    return {
      id: eventId,
      timestamp,
      type: "tool_call",
      granularity: "detailed",
      title: formatPersistedTraceTitle(event),
      description: toolName
        ? `${toolName} ${statusWord}`
        : event.event_type.toLowerCase().replaceAll("_", " "),
    };
  }

  if (event.event_type === "MALICIOUS_EMAIL_READ") {
    return {
      id: eventId,
      timestamp,
      type: "important",
      granularity: "high",
      title: "Malicious email entered model context",
      description: "Assistant read learner-injected malicious email content.",
      important: true,
    };
  }

  if (event.event_type === "TOKEN_DISCLOSURE_ATTEMPTED") {
    return {
      id: eventId,
      timestamp,
      type: "important",
      granularity: "high",
      title: "Token disclosure attempted",
      description: "Assistant attempted to disclose sensitive token material.",
      important: true,
    };
  }

  if (event.event_type === "TOKEN_DISCLOSED") {
    return {
      id: eventId,
      timestamp,
      type: "important",
      granularity: "high",
      title: "Token disclosed",
      description: "Sensitive token was exposed during the session.",
      important: true,
    };
  }

  return null;
}

export function useSessionData({
  sessionId,
}: UseSessionDataParams): UseSessionDataResult {
  const [metadata, setMetadata] = useState<SessionMetadata | null>(null);
  const [metadataReady, setMetadataReady] = useState(false);
  const seenFeedbackKeysRef = useRef(new Set<string>());
  const seenTimelineEventIdsRef = useRef(new Set<string>());
  const seenTelemetryLogIdsRef = useRef(new Set<string>());
  const seenInvoiceIdsRef = useRef(new Set<string>());
  const lab2TelemetryCursorRef = useRef(0);
  const lab3InvoiceCursorRef = useRef(0);
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
            Authorization: AUTH_HEADER,
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
  }, [appendTelemetryLog, appendTimelineEvent, markInvoiceHandled, sessionId]);

  const registerLearnerFeedbackEvents = useCallback(
    (_feedback: LearnerFeedbackItem[], _timestamp: string) => {
      // Metadata polling is the source of truth for feedback.
    },
    [],
  );

  const registerMetadataFeedbackEvents = useCallback(
    (feedbackItems: SessionFeedbackItem[]) => {
      for (const item of feedbackItems) {
        const key = item.id;
        if (seenFeedbackKeysRef.current.has(key)) continue;
        seenFeedbackKeysRef.current.add(key);
        appendTimelineEvent({
          id: `feedback-item-${key}`,
          timestamp: item.created_at,
          type: "explanation",
          granularity: "high",
          title: humanizeFeedbackKey(item.feedback_key),
          description: item.message,
          details: `${item.severity} · ${item.reason_code}`,
          important: item.severity === "error",
        });
      }
    },
    [appendTimelineEvent],
  );

  const refreshSessionMetadata = useCallback(async () => {
    if (!sessionId) return;

    try {
      const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}`, {
        method: "GET",
        headers: {
          Authorization: AUTH_HEADER,
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
      const feedbackItems = Array.isArray(session.feedback_items)
        ? session.feedback_items
        : Array.isArray(session.feedback)
          ? session.feedback
          : [];
      registerMetadataFeedbackEvents(feedbackItems);
    } catch {
      return;
    }
  }, [registerMetadataFeedbackEvents, sessionId]);

  const progressChips = metadata?.progress_chips ?? [];
  const progressReady = metadataReady;
  const sessionState = metadata?.state ?? "UNKNOWN";

  // Initial metadata fetch when the page/session context is ready.
  useEffect(() => {
    setTimelineEvents([]);
    setTelemetryLogs([]);
    setInvoices([]);
    seenTimelineEventIdsRef.current.clear();
    seenTelemetryLogIdsRef.current.clear();
    seenInvoiceIdsRef.current.clear();
    seenFeedbackKeysRef.current.clear();
    lab2TelemetryCursorRef.current = 0;
    lab3InvoiceCursorRef.current = 0;
    setMetadataReady(false);
    void refreshSessionMetadata();
    void refreshTraceTimeline();
  }, [refreshSessionMetadata, refreshTraceTimeline]);

  useEffect(() => {
    if (!sessionId) return;
    const state = (metadata?.state ?? "").toUpperCase();
    const isLab2 = metadata?.lab_id === LAB_2_TOOL_MISUSE_ID;
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

  useEffect(() => {
    if (!sessionId) return;
    const state = (metadata?.state ?? "").toUpperCase();
    const isLab3 = metadata?.lab_id === LAB_3_MEMORY_POISONING_ID;
    if (!isLab3 || (state !== "PROVISIONING" && state !== "ACTIVE")) {
      return;
    }

    let cancelled = false;
    let timeoutId: number | null = null;

    const tick = () => {
      if (cancelled) return;
      const cursor = lab3InvoiceCursorRef.current;
      let item: {
        invoice_id: string;
        vendor_name: string;
        amount: number;
        currency: string;
      };
      if (cursor < LAB3_INVOICE_SEED.length) {
        item = LAB3_INVOICE_SEED[cursor];
      } else {
        const sequence = cursor - LAB3_INVOICE_SEED.length;
        const randomVendorIndex = Math.floor(
          Math.random() * LAB3_FAKE_COMPANIES.length,
        );
        const vendor = LAB3_FAKE_COMPANIES[randomVendorIndex];
        const variation = (Math.random() - 0.5) * 2600;
        const amount = Math.max(
          100,
          Math.round((vendor.base_amount + variation) * 100) / 100,
        );
        item = {
          invoice_id: `inv-${vendor.slug}-2026-${String(sequence + 41).padStart(3, "0")}`,
          vendor_name: vendor.vendor_name,
          amount,
          currency: vendor.currency,
        };
      }
      const now = new Date().toISOString();
      appendInvoice({
        id: `lab3-invoice-${sessionId}-${cursor}`,
        invoice_id: item.invoice_id,
        vendor_name: item.vendor_name,
        amount: item.amount,
        currency: item.currency,
        created_at: now,
        handled_by: null,
        handled_at: null,
      });
      lab3InvoiceCursorRef.current += 1;
      timeoutId = window.setTimeout(tick, LAB3_INVOICE_INTERVAL_MS);
    };

    timeoutId = window.setTimeout(tick, LAB3_INVOICE_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (timeoutId !== null) window.clearTimeout(timeoutId);
    };
  }, [appendInvoice, metadata?.lab_id, metadata?.state, sessionId]);

  // Poll metadata while provisioning/active so session transitions and timed hint unlocks
  // are reflected even if evaluator feedback polling is delayed or unavailable.
  useEffect(() => {
    if (!sessionId) return;
    const state = (metadata?.state ?? "").toUpperCase();
    if (state !== "PROVISIONING" && state !== "ACTIVE") return;

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
