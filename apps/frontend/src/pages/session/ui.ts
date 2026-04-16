import type { CSSProperties } from "react";
import type { LearnerFeedbackStatus } from "./types";

export const API_BASE =
	import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const AUTH_HEADER = "Bearer local:kane:learner";

export const DEMO_H1_STYLE: CSSProperties = {
	color: "#f0fdff",
	textShadow: "0 0 14px rgba(62, 224, 255, 0.45)",
	letterSpacing: 0.5,
};

export const DEMO_H2_STYLE: CSSProperties = {
	color: "#dbf8ff",
	letterSpacing: 0.3,
};

const FEEDBACK_REASON_LABELS: Record<string, string> = {
	PI_GLOBAL_ATTACK_ARTIFACT_CREATED: "Attack artifact created",
	PI_GLOBAL_INBOX_INTERACTION_TRIGGERED: "Inbox tool usage detected",
	PI_GLOBAL_INBOX_INTERACTION_WITHOUT_DISCLOSURE:
		"Inbox reviewed, no secret disclosure yet",
	PI_GLOBAL_MALICIOUS_ARTIFACT_ENTERED_CONTEXT:
		"Malicious content entered model context",
	PI_GLOBAL_POLICY_VIOLATION_ATTEMPTED: "Policy-violation attempt detected",
	PI_GLOBAL_EXPLANATION_MENTIONED_ROOT_CAUSE: "Learner explained root cause",
	PI_GLOBAL_EXPLANATION_MENTIONED_MITIGATION: "Learner proposed mitigation",
	PI_EASY_DIRECT_OVERRIDE_LANGUAGE_USED: "Direct override language used",
	PI_EASY_EXPLANATION_IDENTIFIED_AGENT_TRUSTS_EXERNAL_CONTENT:
		"Learner identified trust-boundary issue",
	PI_EASY_TOKEN_EXPOSED: "Token exposed",
	PI_MEDIUM_COMPLIANCE_AUTHORITY_SPOOFED: "Compliance authority spoofed",
	PI_MEDIUM_AUDIT_URGENCY_INVOKED: "Audit urgency invoked",
	PI_MEDIUM_DISCLOSURE_FRAMED_AS_BUSINESS_REQUIREMENT:
		"Disclosure framed as business requirement",
	PI_MEDIUM_EXPLANATION_IDENTIFIED_RULE_PRIORITY_CLASH:
		"Learner identified rule-priority clash",
	PI_MEDIUM_TOKEN_EXPOSED: "Token exposed",
};

export function formatStatusLabel(status: LearnerFeedbackStatus): string {
	return status.replaceAll("_", " ");
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

export function feedbackTone(status: LearnerFeedbackStatus): {
	border: string;
	background: string;
	color: string;
} {
	if (status === "learned") {
		return {
			border: "1px solid #d94848",
			background: "rgba(120, 22, 22, 0.42)",
			color: "#ffdada",
		};
	}
	if (status === "progress") {
		return {
			border: "1px solid #2f8bc8",
			background: "rgba(18, 55, 83, 0.45)",
			color: "#d6f0ff",
		};
	}
	return {
		border: "1px solid #586879",
		background: "rgba(35, 46, 58, 0.42)",
		color: "#d7e0e7",
	};
}

export function statusTone(state: string | undefined): {
	background: string;
	border: string;
	color: string;
} {
	switch ((state ?? "").toUpperCase()) {
		case "PROVISIONING":
			return {
				background: "rgba(95, 69, 10, 0.72)",
				border: "1px solid #8f7628",
				color: "#ffe6a6",
			};
		case "ACTIVE":
			return {
				background: "rgba(8, 31, 50, 0.72)",
				border: "1px solid #285272",
				color: "#9fe4fb",
			};
		case "COMPLETED":
			return {
				background: "rgba(10, 50, 33, 0.72)",
				border: "1px solid #2e7b57",
				color: "#b9ffe0",
			};
		case "FAILED":
			return {
				background: "rgba(70, 19, 37, 0.72)",
				border: "1px solid #8b3252",
				color: "#ffd1df",
			};
		default:
			return {
				background: "rgba(36, 43, 52, 0.72)",
				border: "1px solid #4a5562",
				color: "#cfd9e2",
			};
	}
}
