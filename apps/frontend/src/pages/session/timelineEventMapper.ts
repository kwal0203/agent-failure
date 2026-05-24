import type { SessionTraceEvent, TimelineEvent } from "./types";

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

export function mapPersistedTraceToTimelineEvent(
  event: SessionTraceEvent,
): TimelineEvent | null {
  const timestamp = event.occurred_at;
  const eventId = `trace-${event.id}`;
  const evidenceFields = {
    report_selectable: event.report_selectable,
    evidence_type: event.evidence_type,
    objective_keys: event.objective_keys,
    why_it_matters: event.why_it_matters,
    default_priority: event.default_priority,
  };
  if (event.event_type === "SESSION_CREATED") {
    return {
      id: eventId,
      timestamp,
      type: "system",
      granularity: "high",
      title: "Session created",
      description: "Lab session was created.",
      ...evidenceFields,
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
      ...evidenceFields,
    };
  }

  if (event.event_type === "ATTACK_EMAIL_SENT") {
    if (event.family !== "learner") {
      return null;
    }
    const subject =
      typeof event.payload.subject === "string" ? event.payload.subject : "";
    const emailFrom =
      typeof event.payload.email_from === "string"
        ? event.payload.email_from
        : "";
    const maliciousMarker = event.payload.malicious_marker === true;
    const emailId =
      typeof event.payload.email_id === "string" && event.payload.email_id
        ? ` (id: ${event.payload.email_id})`
        : "";
    return {
      id: eventId,
      timestamp,
      type: "attacker_action",
      granularity: "high",
      title: maliciousMarker
        ? "Malicious email received"
        : "Benign email received",
      description: `Email accepted${emailId}.`,
      details: `From: ${emailFrom}\nSubject: ${subject}`,
      ...evidenceFields,
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
      ...evidenceFields,
    };
  }

  if (event.event_type === "TRY_ATTACK_CONSOLE_HINT") {
    const hintMessage =
      typeof event.payload.message === "string"
        ? event.payload.message
        : "Try sending an email using the Attack Console.";
    return {
      id: eventId,
      timestamp,
      type: "important",
      granularity: "high",
      title: "Hint: Use Attack Console",
      description: hintMessage,
      important: true,
      ...evidenceFields,
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
      ...evidenceFields,
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
      ...evidenceFields,
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
      ...evidenceFields,
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
      ...evidenceFields,
    };
  }

  return null;
}
