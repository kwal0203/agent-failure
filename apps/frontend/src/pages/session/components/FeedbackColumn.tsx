import type { LearnerFeedbackItem } from "../types";
import {
	DEMO_H2_STYLE,
	feedbackTone,
	formatStatusLabel,
	humanizeReasonCode,
} from "../ui";

type FeedbackColumnProps = {
	feedbackLoading: boolean;
	feedbackError: string | null;
	learnerFeedback: LearnerFeedbackItem[];
};

export function FeedbackColumn({
	feedbackLoading,
	feedbackError,
	learnerFeedback,
}: FeedbackColumnProps) {
	return (
		<section
			style={{
				border: "1px solid #ddd",
				borderRadius: 8,
				padding: 16,
				marginBottom: 16,
				textAlign: "left",
			}}
		>
			<h2 style={DEMO_H2_STYLE}>Learner feedback</h2>
			{feedbackLoading && <p>Loading learner feedback...</p>}
			{feedbackError && <p style={{ color: "red" }}>Error: {feedbackError}</p>}
			{!feedbackLoading && !feedbackError && learnerFeedback.length === 0 && (
				<p>No learner feedback yet.</p>
			)}
			{!feedbackLoading && !feedbackError && learnerFeedback.length > 0 && (
				<ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
					{learnerFeedback.map((item) => {
						const tone = feedbackTone(item.status);
						const normalizedReason = item.reason_code.trim().toLowerCase();
						const normalizedEvidence = item.evidence_snippet
							.trim()
							.toLowerCase();
						const showEvidence =
							normalizedEvidence.length > 0 &&
							normalizedEvidence !== normalizedReason;
						return (
							<li
								key={`${item.reason_code}-${item.status}-${item.evidence_snippet}`}
								style={{
									marginBottom: 8,
									border: tone.border,
									background: tone.background,
									color: tone.color,
									borderRadius: 8,
									padding: "8px 10px",
									listStyle: "none",
								}}
							>
								<p style={{ margin: 0 }}>
									<strong>
										{humanizeReasonCode(item.reason_code)} (
										{formatStatusLabel(item.status)})
									</strong>
								</p>
								{showEvidence && (
									<p style={{ margin: "4px 0 0 0", opacity: 0.95 }}>
										{item.evidence_snippet}
									</p>
								)}
							</li>
						);
					})}
				</ul>
			)}
		</section>
	);
}
