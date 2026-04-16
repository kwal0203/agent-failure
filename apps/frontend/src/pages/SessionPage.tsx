import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useLocation, useParams } from "react-router-dom";
import { useSessionStream } from "../hooks/useSessionStream";

type SessionMetadata = {
	id: string;
	lab_id: string | null;
	lab_version_id: string | null;
	state: string;
	runtime_substate: string | null;
	resume_mode: string;
	interactive: boolean;
	created_at: string;
	started_at: string | null;
	ended_at: string | null;
};

type GetSessionMetadataResponse = {
	session: SessionMetadata;
};

type TranscriptRole = "user" | "agent" | "policy" | "system";

type TranscriptEntry = {
	role: TranscriptRole;
	content: string;
	timestamp: string;
};

type LearnerFeedbackStatus =
	| "learned"
	| "progress"
	| "no_progress"
	| "session_terminal";

type LearnerFeedbackItem = {
	status: LearnerFeedbackStatus;
	reason_code: string;
	evidence_snippet: string;
};

type GetFeedbackResponse = {
	feedback: LearnerFeedbackItem[];
};

type InjectSessionEmailResponse = {
	session_id: string;
	email_id: string | null;
	accepted: boolean;
};

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const AUTH_HEADER = "Bearer local:kane:learner";
const DEMO_H1_STYLE = {
	color: "#f0fdff",
	textShadow: "0 0 14px rgba(62, 224, 255, 0.45)",
	letterSpacing: 0.5,
};
const DEMO_H2_STYLE = {
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

function formatStatusLabel(status: LearnerFeedbackStatus): string {
	return status.replaceAll("_", " ");
}

function humanizeReasonCode(reasonCode: string): string {
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

function feedbackTone(status: LearnerFeedbackStatus): {
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

function statusTone(state: string | undefined): {
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

export default function SessionPage() {
	const { sessionId } = useParams<{ sessionId: string }>();
	const location = useLocation();
	const { connectionState, messages, sendPrompt } = useSessionStream(sessionId);
	const routeState = (
		typeof location.state === "object" && location.state !== null
			? location.state
			: {}
	) as { labName?: string };
	const headingText =
		typeof routeState.labName === "string" &&
		routeState.labName.trim().length > 0
			? routeState.labName
			: "Session";
	const processedMessageCount = useRef(0);
	const transcriptViewportRef = useRef<HTMLDivElement | null>(null);
	const activeEntryTsRef = useRef<string | null>(null);
	const displayedEntryRef = useRef("");
	const pendingBufferRef = useRef("");
	const finalizePendingRef = useRef(false);
	const animationFrameRef = useRef<number | null>(null);
	const lastRevealAtMsRef = useRef(0);
	const [metadata, setMetadata] = useState<SessionMetadata | null>(null);
	const [feedbackError, setFeedbackError] = useState<string | null>(null);
	const [feedbackLoading, setFeedbackLoading] = useState(false);
	const [prompt, setPrompt] = useState("");
	const [transcriptEntries, setTranscriptEntries] = useState<TranscriptEntry[]>(
		[],
	);
	const [activeEntry, setActiveEntry] = useState("");
	const [isAwaitingResponse, setIsAwaitingResponse] = useState(false);
	const [learnerFeedback, setLearnerFeedback] = useState<LearnerFeedbackItem[]>(
		[],
	);
	const [emailFrom, setEmailFrom] = useState("");
	const [emailSubject, setEmailSubject] = useState("");
	const [emailBody, setEmailBody] = useState("");
	const [emailMalicious, setEmailMalicious] = useState(true);
	const [injectingEmail, setInjectingEmail] = useState(false);
	const [injectEmailError, setInjectEmailError] = useState<string | null>(null);
	const [injectEmailResult, setInjectEmailResult] = useState<string | null>(
		null,
	);

	const resetActiveStream = useCallback(() => {
		displayedEntryRef.current = "";
		pendingBufferRef.current = "";
		finalizePendingRef.current = false;
		activeEntryTsRef.current = null;
		setActiveEntry("");
		if (animationFrameRef.current !== null) {
			cancelAnimationFrame(animationFrameRef.current);
			animationFrameRef.current = null;
		}
	}, []);

	const drainRevealFrame = useCallback(() => {
		const revealIntervalMs = 60;
		const now = performance.now();
		if (now - lastRevealAtMsRef.current < revealIntervalMs) {
			animationFrameRef.current = requestAnimationFrame(drainRevealFrame);
			return;
		}

		if (pendingBufferRef.current.length > 0) {
			const buffer = pendingBufferRef.current;
			const match = buffer.match(/^(\s*\S+\s*)/);
			const reveal = match ? match[1] : buffer;
			pendingBufferRef.current = buffer.slice(reveal.length);
			displayedEntryRef.current += reveal;
			lastRevealAtMsRef.current = now;
			setActiveEntry(displayedEntryRef.current);
			animationFrameRef.current = requestAnimationFrame(drainRevealFrame);
			return;
		}

		if (finalizePendingRef.current) {
			const finalized = displayedEntryRef.current.trim();
			if (finalized) {
				setTranscriptEntries((entries) => {
					const last = entries.length > 0 ? entries[entries.length - 1] : null;
					if (
						last &&
						last.role === "agent" &&
						last.content === finalized &&
						last.timestamp ===
							(activeEntryTsRef.current ?? new Date().toISOString())
					) {
						return entries;
					}
					return [
						...entries,
						{
							role: "agent",
							content: finalized,
							timestamp: activeEntryTsRef.current ?? new Date().toISOString(),
						},
					];
				});
			}
			resetActiveStream();
			setIsAwaitingResponse(false);
			return;
		}

		animationFrameRef.current = null;
	}, [resetActiveStream]);

	const ensureRevealLoop = useCallback(() => {
		if (animationFrameRef.current === null) {
			animationFrameRef.current = requestAnimationFrame(drainRevealFrame);
		}
	}, [drainRevealFrame]);

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
			setMetadata(data.session);
		} catch {}
	}, [sessionId]);

	useEffect(() => {
		void refreshSessionMetadata();
	}, [refreshSessionMetadata]);

	useEffect(() => {
		if (!sessionId) return;
		if (metadata?.state !== "PROVISIONING") return;

		const intervalId = window.setInterval(() => {
			void refreshSessionMetadata();
		}, 2000);

		return () => {
			window.clearInterval(intervalId);
		};
	}, [sessionId, metadata?.state, refreshSessionMetadata]);

	useEffect(() => {
		if (!sessionId) return;

		let cancelled = false;
		const run = async (opts?: { background?: boolean }) => {
			if (!opts?.background) {
				setFeedbackLoading(true);
				setFeedbackError(null);
			}

			try {
				const res = await fetch(
					`${API_BASE}/api/v1/sessions/${sessionId}/evaluator-feedback`,
					{
						method: "GET",
						headers: {
							Authorization: AUTH_HEADER,
							"Content-Type": "application/json",
						},
					},
				);

				if (!res.ok) {
					if (!cancelled && !opts?.background) {
						setFeedbackError(`HTTP ${res.status}`);
					}
					return;
				}

				const data = (await res.json()) as GetFeedbackResponse;
				if (!cancelled) {
					setLearnerFeedback(data.feedback);
				}
			} catch (e) {
				if (!cancelled && !opts?.background) {
					setFeedbackError(e instanceof Error ? e.message : "request failed");
				}
			} finally {
				if (!cancelled && !opts?.background) {
					setFeedbackLoading(false);
				}
			}
		};

		void run();

		const intervalId = window.setInterval(() => {
			void run({ background: true });
		}, 3000);

		return () => {
			cancelled = true;
			window.clearInterval(intervalId);
		};
	}, [sessionId]);

	useEffect(() => {
		if (processedMessageCount.current > messages.length) {
			processedMessageCount.current = 0;
		}

		const newMessages = messages.slice(processedMessageCount.current);
		if (newMessages.length === 0) return;

		for (const message of newMessages) {
			if (message.type === "SESSION_STATUS") {
				setMetadata((prev) =>
					prev
						? {
								...prev,
								state: message.payload.state,
								runtime_substate: message.payload.runtime_substate,
								interactive: message.payload.interactive,
							}
						: prev,
				);
				continue;
			}

			if (message.type === "AGENT_TEXT_CHUNK") {
				if (!activeEntryTsRef.current) {
					activeEntryTsRef.current = message.timestamp;
				}
				pendingBufferRef.current += message.payload.content;
				if (message.payload.final) {
					finalizePendingRef.current = true;
				}
				ensureRevealLoop();
				continue;
			}

			if (message.type === "POLICY_DENIAL") {
				setTranscriptEntries((entries) => [
					...entries,
					{
						role: "policy",
						content: message.payload.message,
						timestamp: message.timestamp,
					},
				]);
				setIsAwaitingResponse(false);
				continue;
			}

			if (message.type === "TRACE_EVENT") {
				if (
					message.payload.event_code === "TURN_STARTED" ||
					message.payload.event_code === "MODEL_REQUEST_STARTED"
				) {
					continue;
				}
				setTranscriptEntries((entries) => [
					...entries,
					{
						role: "system",
						content: `[${message.payload.event_code}] ${message.payload.message}`,
						timestamp: message.timestamp,
					},
				]);
				continue;
			}

			if (message.type === "SYSTEM_ERROR") {
				setTranscriptEntries((entries) => [
					...entries,
					{
						role: "system",
						content: message.payload.message,
						timestamp: message.timestamp,
					},
				]);
				setIsAwaitingResponse(false);
				continue;
			}

			if (message.type === "LEARNER_FEEDBACK") {
				setLearnerFeedback(message.payload.feedback);
			}
		}

		processedMessageCount.current = messages.length;
	}, [messages, ensureRevealLoop]);

	const onSubmitPrompt = (e: React.FormEvent<HTMLFormElement>) => {
		e.preventDefault();
		const text = prompt.trim();
		if (!text) return;
		setTranscriptEntries((entries) => [
			...entries,
			{
				role: "user",
				content: text,
				timestamp: new Date().toISOString(),
			},
		]);
		resetActiveStream();
		setIsAwaitingResponse(true);
		sendPrompt(text);
		setPrompt("");
	};

	const onSubmitEmail = async (e: React.FormEvent<HTMLFormElement>) => {
		e.preventDefault();
		if (!sessionId) return;

		const sender = emailFrom.trim();
		const subject = emailSubject.trim();
		const body = emailBody.trim();
		if (!sender || !subject || !body) {
			setInjectEmailError("From, subject, and body are required.");
			return;
		}

		setInjectingEmail(true);
		setInjectEmailError(null);
		setInjectEmailResult(null);
		try {
			const res = await fetch(
				`${API_BASE}/api/v1/sessions/${sessionId}/inbox/email`,
				{
					method: "POST",
					headers: {
						Authorization: AUTH_HEADER,
						"Content-Type": "application/json",
					},
					body: JSON.stringify({
						email_from: sender,
						email_subject: subject,
						email_body: body,
						malicious: emailMalicious,
						source: "learner",
					}),
				},
			);

			const payload = (await res.json()) as
				| InjectSessionEmailResponse
				| { error?: { message?: string } };
			if (!res.ok) {
				const msg =
					"error" in payload && payload.error?.message
						? payload.error.message
						: `HTTP ${res.status}`;
				setInjectEmailError(msg);
				return;
			}

			const accepted =
				"accepted" in payload && payload.accepted ? "accepted" : "submitted";
			const emailId =
				"email_id" in payload && payload.email_id
					? ` (id: ${payload.email_id})`
					: "";
			setInjectEmailResult(`Email ${accepted}${emailId}.`);
		} catch (err) {
			setInjectEmailError(
				err instanceof Error ? err.message : "request failed",
			);
		} finally {
			setInjectingEmail(false);
		}
	};

	const canSend =
		connectionState === "open" &&
		!isAwaitingResponse &&
		(metadata?.interactive ?? false);

	const formatTime = (isoTs: string) => {
		const date = new Date(isoTs);
		if (Number.isNaN(date.getTime())) return isoTs;
		return date.toLocaleTimeString();
	};

	const activeTokens = activeEntry.match(/(\s+|\S+)/g) ?? [];
	const currentState = metadata?.state ?? "UNKNOWN";
	const tone = statusTone(currentState);
	const runtimeSuffix = metadata?.runtime_substate
		? ` · ${metadata.runtime_substate}`
		: "";

	useEffect(() => {
		const viewport = transcriptViewportRef.current;
		if (!viewport) return;
		viewport.scrollTop = viewport.scrollHeight;
	}, []);

	useEffect(() => {
		return () => {
			if (animationFrameRef.current !== null) {
				cancelAnimationFrame(animationFrameRef.current);
			}
		};
	}, []);

	return (
		<main style={{ maxWidth: 960, margin: "0 auto", padding: "24px" }}>
			<header
				style={{
					marginBottom: "16px",
					display: "flex",
					alignItems: "center",
					justifyContent: "space-between",
					gap: 12,
					flexWrap: "wrap",
				}}
			>
				<h1 style={{ ...DEMO_H1_STYLE, margin: 0 }}>{headingText}</h1>
				<div
					style={{
						fontSize: 13,
						background: tone.background,
						border: tone.border,
						color: tone.color,
						padding: "6px 10px",
						borderRadius: 8,
						transition:
							"background-color 260ms ease, border-color 260ms ease, color 260ms ease",
					}}
				>
					Status: <strong>{currentState}</strong>
					{runtimeSuffix}
				</div>
			</header>

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
							onChange={(e) => setEmailFrom(e.target.value)}
							style={{ width: "100%", marginTop: 4 }}
							disabled={injectingEmail}
						/>
					</label>
					<label style={{ display: "block", marginBottom: 8 }}>
						Subject
						<input
							type="text"
							value={emailSubject}
							onChange={(e) => setEmailSubject(e.target.value)}
							style={{ width: "100%", marginTop: 4 }}
							disabled={injectingEmail}
						/>
					</label>
					<label style={{ display: "block", marginBottom: 8 }}>
						Body
						<textarea
							rows={4}
							value={emailBody}
							onChange={(e) => setEmailBody(e.target.value)}
							style={{ width: "100%", marginTop: 4 }}
							disabled={injectingEmail}
						/>
					</label>
					<label style={{ display: "inline-flex", gap: 8, marginBottom: 12 }}>
						<input
							type="checkbox"
							checked={emailMalicious}
							onChange={(e) => setEmailMalicious(e.target.checked)}
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
				{feedbackError && (
					<p style={{ color: "red" }}>Error: {feedbackError}</p>
				)}
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

			<section
				ref={transcriptViewportRef}
				style={{
					border: "1px solid #ddd",
					borderRadius: 8,
					padding: 16,
					marginBottom: 16,
					minHeight: 220,
					maxHeight: 420,
					overflowY: "auto",
					textAlign: "left",
				}}
			>
				<h2 style={DEMO_H2_STYLE}>Transcript</h2>
				{transcriptEntries.length === 0 && !activeEntry && (
					<p style={{ margin: 0 }}>(streamed agent text will appear here)</p>
				)}
				{transcriptEntries.map((entry, index) => (
					<div
						key={`${entry.timestamp}-${entry.role}-${entry.content.slice(0, 20)}`}
					>
						<p style={{ margin: "8px 0 4px 0", fontSize: 12, opacity: 0.7 }}>
							<strong>{entry.role.toUpperCase()}</strong>{" "}
							{formatTime(entry.timestamp)}
						</p>
						<div className="transcript-markdown" style={{ margin: 0 }}>
							<ReactMarkdown>{entry.content}</ReactMarkdown>
						</div>
						{index < transcriptEntries.length - 1 && <hr />}
					</div>
				))}
				{isAwaitingResponse && !activeEntry && (
					<div style={{ marginTop: 12 }}>
						<p style={{ margin: "8px 0 4px 0", fontSize: 12, opacity: 0.7 }}>
							<strong>AGENT</strong> thinking
							<span className="thinking-dots" aria-hidden="true">
								<span>.</span>
								<span>.</span>
								<span>.</span>
							</span>
						</p>
					</div>
				)}
				{activeEntry && (
					<div style={{ marginTop: 12 }}>
						<p style={{ margin: "8px 0 4px 0", fontSize: 12, opacity: 0.7 }}>
							<strong>AGENT</strong> streaming...
						</p>
						<div style={{ whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
							{(() => {
								let tokenOffset = 0;
								return activeTokens.map((token) => {
									const key = `${tokenOffset}-${token}`;
									tokenOffset += token.length;
									return (
										<span
											key={key}
											style={{
												display: "inline",
												opacity: 0,
												transform: "translateX(6px)",
												animationName: "wordIn",
												animationDuration: "220ms",
												animationTimingFunction: "ease-out",
												animationFillMode: "forwards",
											}}
										>
											{token}
										</span>
									);
								});
							})()}
						</div>
					</div>
				)}
			</section>

			<style>{`
        @keyframes wordIn {
          from { opacity: 0; transform: translateX(6px); }
          to { opacity: 1; transform: translateX(0); }
        }
        .transcript-markdown p {
          margin: 0 0 0.9em 0;
        }
        .transcript-markdown p:last-child {
          margin-bottom: 0;
        }
        .thinking-dots span {
          opacity: 0.2;
          animation: thinkingDot 1.2s infinite;
        }
        .thinking-dots span:nth-child(2) {
          animation-delay: 0.2s;
        }
        .thinking-dots span:nth-child(3) {
          animation-delay: 0.4s;
        }
        @keyframes thinkingDot {
          0% { opacity: 0.2; }
          50% { opacity: 1; }
          100% { opacity: 0.2; }
        }
      `}</style>

			<section
				style={{ border: "1px solid #ddd", borderRadius: 8, padding: 16 }}
			>
				<h2 style={DEMO_H2_STYLE}>Prompt</h2>
				<form onSubmit={onSubmitPrompt}>
					<textarea
						rows={4}
						placeholder="Type your prompt..."
						style={{ width: "100%", marginBottom: 12 }}
						value={prompt}
						onChange={(e) => setPrompt(e.target.value)}
						disabled={!canSend}
					/>
					<button type="submit" disabled={!canSend}>
						Send
					</button>
					{!canSend && (
						<p style={{ marginTop: 8, opacity: 0.8 }}>
							Prompt disabled: socket must be open, session interactive, and no
							turn in progress.
						</p>
					)}
				</form>
			</section>
		</main>
	);
}
