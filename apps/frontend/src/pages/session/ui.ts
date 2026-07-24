import { getCurrentAuthHeader } from "../../auth/session";
import { getApiBaseUrl } from "../../config";
import type { LearnerFeedbackStatus } from "./types";

export const API_BASE = getApiBaseUrl();
export function getAuthHeader(): Promise<string> {
  return getCurrentAuthHeader();
}

const FEEDBACK_REASON_LABELS: Record<string, string> = {
  PI_ATTACK_ARTIFACT_CREATED: "Attack artifact created",
  PI_INBOX_INTERACTION_TRIGGERED: "Inbox tool usage detected",
  PI_INBOX_INTERACTION_WITHOUT_DISCLOSURE:
    "Inbox reviewed, no secret disclosure yet",
  PI_MALICIOUS_ARTIFACT_ENTERED_CONTEXT:
    "Malicious content entered model context",
  PI_POLICY_VIOLATION_ATTEMPTED: "Policy-violation attempt detected",
  PI_EXPLANATION_MENTIONED_ROOT_CAUSE: "Learner explained root cause",
  PI_EXPLANATION_MENTIONED_MITIGATION: "Learner proposed mitigation",
  PI_COMPLIANCE_AUTHORITY_SPOOFED: "Compliance authority spoofed",
  PI_AUDIT_URGENCY_INVOKED: "Audit urgency invoked",
  PI_DISCLOSURE_FRAMED_AS_BUSINESS_REQUIREMENT:
    "Disclosure framed as business requirement",
  PI_EXPLANATION_IDENTIFIED_RULE_PRIORITY_CLASH:
    "Learner identified rule-priority clash",
  PI_TOKEN_EXPOSED: "Private information revealed",
};

const FEEDBACK_KEY_LABELS: Record<string, string> = {
  lab1_benign_email_not_progressing: "Benign email sent",
};

export function formatStatusLabel(status: LearnerFeedbackStatus): string {
  return status.replaceAll("_", " ");
}

export function humanizeFeedbackKey(feedbackKey: string): string {
  const mapped = FEEDBACK_KEY_LABELS[feedbackKey];
  if (mapped) return mapped;

  return feedbackKey
    .trim()
    .toLowerCase()
    .split("_")
    .filter((token) => token.length > 0)
    .map((token, index) =>
      index === 0 ? token.charAt(0).toUpperCase() + token.slice(1) : token,
    )
    .join(" ");
}

export function humanizeReasonCode(reasonCode: string): string {
  const mapped = FEEDBACK_REASON_LABELS[reasonCode];
  if (mapped) return mapped;

  const stripped = reasonCode
    .replace(/^PI_(GLOBAL|EASY|MEDIUM|HARD)_/, "")
    .replace(/^PI_/, "");
  return stripped
    .toLowerCase()
    .split("_")
    .filter((token) => token.length > 0)
    .map((token, index) =>
      index === 0 ? token.charAt(0).toUpperCase() + token.slice(1) : token,
    )
    .join(" ");
}
