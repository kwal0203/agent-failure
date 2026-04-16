import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useSessionStream } from "../hooks/useSessionStream";
import { FeedbackColumn } from "./session/components/FeedbackColumn";
import { LabGuideColumn } from "./session/components/LabGuideColumn";
import { WorkspaceColumn } from "./session/components/WorkspaceColumn";
import type {
	GetFeedbackResponse,
	GetSessionMetadataResponse,
	InjectSessionEmailResponse,
	LearnerFeedbackItem,
	SessionMetadata,
	SessionWorkspaceState,
	TranscriptEntry,
} from "./session/types";
import { API_BASE, AUTH_HEADER, DEMO_H1_STYLE, statusTone } from "./session/ui";

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
	const [workspaceState] = useState<SessionWorkspaceState>({
		selectedTool: "email",
		toolPaneOpen: true,
		transcriptAutoScrollEnabled: true,
		feedbackPanelVisible: true,
	});

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

			{workspaceState.toolPaneOpen &&
				workspaceState.selectedTool === "email" && (
					<LabGuideColumn
						emailFrom={emailFrom}
						emailSubject={emailSubject}
						emailBody={emailBody}
						emailMalicious={emailMalicious}
						injectingEmail={injectingEmail}
						sessionId={sessionId}
						injectEmailError={injectEmailError}
						injectEmailResult={injectEmailResult}
						onSubmitEmail={onSubmitEmail}
						onEmailFromChange={setEmailFrom}
						onEmailSubjectChange={setEmailSubject}
						onEmailBodyChange={setEmailBody}
						onEmailMaliciousChange={setEmailMalicious}
					/>
				)}

			{workspaceState.feedbackPanelVisible && (
				<FeedbackColumn
					feedbackLoading={feedbackLoading}
					feedbackError={feedbackError}
					learnerFeedback={learnerFeedback}
				/>
			)}

			<WorkspaceColumn
				transcriptViewportRef={transcriptViewportRef}
				transcriptEntries={transcriptEntries}
				activeEntry={activeEntry}
				activeTokens={activeTokens}
				isAwaitingResponse={isAwaitingResponse}
				prompt={prompt}
				canSend={canSend}
				onPromptChange={setPrompt}
				onSubmitPrompt={onSubmitPrompt}
				formatTime={formatTime}
			/>
		</main>
	);
}
