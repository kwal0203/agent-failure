import type { FormEvent } from "react";

type EmailToolFormProps = {
	emailFrom: string;
	emailSubject: string;
	emailBody: string;
	emailMalicious: boolean;
	injectingEmail: boolean;
	sessionId?: string;
	injectEmailError: string | null;
	injectEmailResult: string | null;
	onSubmitEmail: (e: FormEvent<HTMLFormElement>) => void;
	onResetEmail: () => void;
	onEmailFromChange: (value: string) => void;
	onEmailSubjectChange: (value: string) => void;
	onEmailBodyChange: (value: string) => void;
	onEmailMaliciousChange: (value: boolean) => void;
};

export function EmailToolForm({
	emailFrom,
	emailSubject,
	emailBody,
	emailMalicious,
	injectingEmail,
	sessionId,
	injectEmailError,
	injectEmailResult,
	onSubmitEmail,
	onResetEmail,
	onEmailFromChange,
	onEmailSubjectChange,
	onEmailBodyChange,
	onEmailMaliciousChange,
}: EmailToolFormProps) {
	return (
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
			<div style={{ display: "flex", gap: 8 }}>
				<button type="submit" disabled={injectingEmail || !sessionId}>
					{injectingEmail ? "Injecting..." : "Inject Email"}
				</button>
				<button type="button" onClick={onResetEmail} disabled={injectingEmail}>
					Reset
				</button>
			</div>
			{injectEmailError && (
				<p style={{ color: "red", marginTop: 8 }}>{injectEmailError}</p>
			)}
			{injectEmailResult && (
				<p style={{ color: "green", marginTop: 8 }}>{injectEmailResult}</p>
			)}
		</form>
	);
}
