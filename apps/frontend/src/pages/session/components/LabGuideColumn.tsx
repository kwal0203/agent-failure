import type { FormEvent } from "react";
import { DEMO_H2_STYLE } from "../ui";

type LabGuideColumnProps = {
	emailFrom: string;
	emailSubject: string;
	emailBody: string;
	emailMalicious: boolean;
	injectingEmail: boolean;
	sessionId?: string;
	injectEmailError: string | null;
	injectEmailResult: string | null;
	onSubmitEmail: (e: FormEvent<HTMLFormElement>) => void;
	onEmailFromChange: (value: string) => void;
	onEmailSubjectChange: (value: string) => void;
	onEmailBodyChange: (value: string) => void;
	onEmailMaliciousChange: (value: boolean) => void;
};

export function LabGuideColumn({
	emailFrom,
	emailSubject,
	emailBody,
	emailMalicious,
	injectingEmail,
	sessionId,
	injectEmailError,
	injectEmailResult,
	onSubmitEmail,
	onEmailFromChange,
	onEmailSubjectChange,
	onEmailBodyChange,
	onEmailMaliciousChange,
}: LabGuideColumnProps) {
	return (
		<section
			style={{
				border: "1px solid #ddd",
				borderRadius: 8,
				padding: 16,
				marginBottom: 16,
			}}
		>
			<h2 style={DEMO_H2_STYLE}>Attacker Console</h2>
			<form onSubmit={onSubmitEmail}>
				<label style={{ display: "block", marginBottom: 8 }}>
					From
					<input
						type="text"
						value={emailFrom}
						onChange={(e) => onEmailFromChange(e.target.value)}
						style={{ width: "100%", marginTop: 4 }}
						disabled={injectingEmail}
					/>
				</label>
				<label style={{ display: "block", marginBottom: 8 }}>
					Subject
					<input
						type="text"
						value={emailSubject}
						onChange={(e) => onEmailSubjectChange(e.target.value)}
						style={{ width: "100%", marginTop: 4 }}
						disabled={injectingEmail}
					/>
				</label>
				<label style={{ display: "block", marginBottom: 8 }}>
					Body
					<textarea
						rows={4}
						value={emailBody}
						onChange={(e) => onEmailBodyChange(e.target.value)}
						style={{ width: "100%", marginTop: 4 }}
						disabled={injectingEmail}
					/>
				</label>
				<label style={{ display: "inline-flex", gap: 8, marginBottom: 12 }}>
					<input
						type="checkbox"
						checked={emailMalicious}
						onChange={(e) => onEmailMaliciousChange(e.target.checked)}
						disabled={injectingEmail}
					/>
					Mark as malicious
				</label>
				<div>
					<button type="submit" disabled={injectingEmail || !sessionId}>
						{injectingEmail ? "Injecting..." : "Inject Email"}
					</button>
				</div>
				{injectEmailError && (
					<p style={{ color: "red", marginTop: 8 }}>{injectEmailError}</p>
				)}
				{injectEmailResult && (
					<p style={{ color: "green", marginTop: 8 }}>{injectEmailResult}</p>
				)}
			</form>
		</section>
	);
}
