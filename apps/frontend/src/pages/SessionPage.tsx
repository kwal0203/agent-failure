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
	TimelineEvent,
	ToolKey,
	TranscriptEntry,
} from "./session/types";
import {
	API_BASE,
	AUTH_HEADER,
	DEMO_H1_STYLE,
	formatStatusLabel,
	humanizeReasonCode,
	statusTone,
} from "./session/ui";

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
	const [_learnerFeedback, setLearnerFeedback] = useState<
		LearnerFeedbackItem[]
	>([]);
	const [emailFrom, setEmailFrom] = useState("");
	const [emailSubject, setEmailSubject] = useState("");
	const [emailBody, setEmailBody] = useState("");
	const [emailMalicious, setEmailMalicious] = useState(true);
	const [injectingEmail, setInjectingEmail] = useState(false);
	const [injectEmailError, setInjectEmailError] = useState<string | null>(null);
	const [injectEmailResult, setInjectEmailResult] = useState<string | null>(
		null,
	);
	const [workspaceState, setWorkspaceState] = useState<SessionWorkspaceState>({
		selectedTool: null,
		toolPaneOpen: false,
		transcriptAutoScrollEnabled: true,
		feedbackPanelVisible: true,
	});
	const [showJumpToLatest, setShowJumpToLatest] = useState(false);
	const transcriptContentSnapshotRef = useRef({ entries: 0, activeLength: 0 });
	const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
	const seenTimelineEventIdsRef = useRef(new Set<string>());
	const seenFeedbackKeysRef = useRef(new Set<string>());

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

	const appendTimelineEvent = useCallback((event: TimelineEvent) => {
		if (seenTimelineEventIdsRef.current.has(event.id)) {
			return;
		}
		seenTimelineEventIdsRef.current.add(event.id);
		setTimelineEvents((prev) => [...prev, event]);
	}, []);

	const registerLearnerFeedbackEvents = useCallback(
		(feedback: LearnerFeedbackItem[], timestamp: string) => {
			for (const item of feedback) {
				const key = `${item.status}|${item.reason_code}|${item.evidence_snippet}`;
				if (seenFeedbackKeysRef.current.has(key)) continue;
				seenFeedbackKeysRef.current.add(key);
				appendTimelineEvent({
					id: `feedback-${key}`,
					timestamp,
					type: "explanation",
					granularity: "high",
					title: humanizeReasonCode(item.reason_code),
					description: "Placeholder",
					details: `Feedback status: ${formatStatusLabel(item.status)}`,
					important: item.status === "learned",
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
					registerLearnerFeedbackEvents(
						data.feedback,
						new Date().toISOString(),
					);
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
	}, [sessionId, registerLearnerFeedbackEvents]);

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
				appendTimelineEvent({
					id: `status-${message.timestamp}-${message.payload.state}-${message.payload.runtime_substate ?? "none"}`,
					timestamp: message.timestamp,
					type: "system",
					granularity: "high",
					title: "Session status updated",
					description: `${message.payload.state}${message.payload.runtime_substate ? ` · ${message.payload.runtime_substate}` : ""}`,
				});
				continue;
			}

			if (message.type === "AGENT_TEXT_CHUNK") {
				if (!activeEntryTsRef.current) {
					activeEntryTsRef.current = message.timestamp;
				}
				pendingBufferRef.current += message.payload.content;
				if (message.payload.final) {
					finalizePendingRef.current = true;
					appendTimelineEvent({
						id: `agent-final-${message.timestamp}`,
						timestamp: message.timestamp,
						type: "agent_action",
						granularity: "detailed",
						title: "Agent response completed",
						description: "A streamed response finished in the transcript.",
					});
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
				appendTimelineEvent({
					id: `policy-denial-${message.timestamp}-${message.payload.code}`,
					timestamp: message.timestamp,
					type: "important",
					granularity: "high",
					title: "Policy denial",
					description: message.payload.message,
					details: `Policy code: ${message.payload.code}`,
					important: true,
				});
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
				appendTimelineEvent({
					id: `trace-${message.timestamp}-${message.payload.event_code}`,
					timestamp: message.timestamp,
					type: message.payload.event_code.includes("TOOL")
						? "tool_call"
						: "system",
					granularity: "detailed",
					title: message.payload.event_code,
					description: message.payload.message,
				});
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
				appendTimelineEvent({
					id: `system-error-${message.timestamp}-${message.payload.code}`,
					timestamp: message.timestamp,
					type: "important",
					granularity: "high",
					title: "System error",
					description: message.payload.message,
					details: `Error code: ${message.payload.code}`,
					important: true,
				});
				continue;
			}

			if (message.type === "LEARNER_FEEDBACK") {
				setLearnerFeedback(message.payload.feedback);
				registerLearnerFeedbackEvents(
					message.payload.feedback,
					message.timestamp,
				);
			}
		}

		processedMessageCount.current = messages.length;
	}, [
		messages,
		ensureRevealLoop,
		appendTimelineEvent,
		registerLearnerFeedbackEvents,
	]);

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
				appendTimelineEvent({
					id: `email-inject-error-${new Date().toISOString()}-${res.status}`,
					timestamp: new Date().toISOString(),
					type: "system",
					granularity: "high",
					title: "Email injection failed",
					description: msg,
					important: true,
				});
				return;
			}

			const accepted =
				"accepted" in payload && payload.accepted ? "accepted" : "submitted";
			const emailId =
				"email_id" in payload && payload.email_id
					? ` (id: ${payload.email_id})`
					: "";
			setInjectEmailResult(`Email ${accepted}${emailId}.`);
			appendTimelineEvent({
				id: `email-inject-${new Date().toISOString()}-${sender}-${subject}`,
				timestamp: new Date().toISOString(),
				type: "attacker_action",
				granularity: "high",
				title: "Email injected to inbox",
				description: `Email ${accepted}${emailId}.`,
				details: `From: ${sender}\nSubject: ${subject}`,
			});
		} catch (err) {
			const message = err instanceof Error ? err.message : "request failed";
			setInjectEmailError(message);
			appendTimelineEvent({
				id: `email-inject-error-${new Date().toISOString()}-exception`,
				timestamp: new Date().toISOString(),
				type: "system",
				granularity: "high",
				title: "Email injection failed",
				description: message,
				important: true,
			});
		} finally {
			setInjectingEmail(false);
		}
	};

	const onResetEmail = () => {
		setEmailFrom("");
		setEmailSubject("");
		setEmailBody("");
		setEmailMalicious(true);
		setInjectEmailError(null);
		setInjectEmailResult(null);
	};

	const canSend =
		connectionState === "open" &&
		!isAwaitingResponse &&
		(metadata?.interactive ?? false);

	const onToolSelect = (tool: ToolKey) => {
		setWorkspaceState((prev) => {
			if (prev.toolPaneOpen && prev.selectedTool === tool) {
				return {
					...prev,
					toolPaneOpen: false,
				};
			}
			return {
				...prev,
				selectedTool: tool,
				toolPaneOpen: true,
			};
		});
	};

	const scrollTranscriptToBottom = useCallback(() => {
		const viewport = transcriptViewportRef.current;
		if (!viewport) return;
		viewport.scrollTop = viewport.scrollHeight;
	}, []);

	const onTranscriptScroll = useCallback(() => {
		const viewport = transcriptViewportRef.current;
		if (!viewport) return;
		const remaining =
			viewport.scrollHeight - viewport.clientHeight - viewport.scrollTop;
		const nearBottom = remaining <= 48;

		setWorkspaceState((prev) => {
			if (prev.transcriptAutoScrollEnabled === nearBottom) {
				return prev;
			}
			return {
				...prev,
				transcriptAutoScrollEnabled: nearBottom,
			};
		});

		if (nearBottom) {
			setShowJumpToLatest(false);
		}
	}, []);

	const onJumpToLatest = useCallback(() => {
		scrollTranscriptToBottom();
		setWorkspaceState((prev) => ({
			...prev,
			transcriptAutoScrollEnabled: true,
		}));
		setShowJumpToLatest(false);
	}, [scrollTranscriptToBottom]);

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
		const nextSnapshot = {
			entries: transcriptEntries.length,
			activeLength: activeEntry.length,
		};
		const previous = transcriptContentSnapshotRef.current;
		const hasNewTranscriptContent =
			nextSnapshot.entries > previous.entries ||
			nextSnapshot.activeLength > previous.activeLength;

		transcriptContentSnapshotRef.current = nextSnapshot;
		if (!hasNewTranscriptContent) return;

		if (workspaceState.transcriptAutoScrollEnabled) {
			scrollTranscriptToBottom();
			setShowJumpToLatest(false);
			return;
		}

		setShowJumpToLatest(true);
	}, [
		transcriptEntries,
		activeEntry,
		workspaceState.transcriptAutoScrollEnabled,
		scrollTranscriptToBottom,
	]);

	useEffect(() => {
		scrollTranscriptToBottom();
	}, [scrollTranscriptToBottom]);

	useEffect(() => {
		return () => {
			if (animationFrameRef.current !== null) {
				cancelAnimationFrame(animationFrameRef.current);
			}
		};
	}, []);

	return (
		<main
			style={{
				height: "100vh",
				padding: 16,
				boxSizing: "border-box",
				display: "flex",
				flexDirection: "column",
				overflow: "hidden",
			}}
		>
			<header
				style={{
					flex: "0 0 auto",
					marginBottom: 16,
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

			<div
				style={{
					display: "grid",
					gridTemplateColumns:
						"minmax(280px, 24%) minmax(520px, 1fr) minmax(300px, 28%)",
					gap: 16,
					flex: "1 1 auto",
					minHeight: 0,
					overflow: "hidden",
				}}
			>
				<aside style={{ minHeight: 0, overflowY: "auto" }}>
					<LabGuideColumn />
				</aside>

				<section
					style={{
						minHeight: 0,
						minWidth: 0,
						overflow: "hidden",
					}}
				>
					<WorkspaceColumn
						transcriptViewportRef={transcriptViewportRef}
						transcriptEntries={transcriptEntries}
						activeEntry={activeEntry}
						activeTokens={activeTokens}
						isAwaitingResponse={isAwaitingResponse}
						selectedTool={workspaceState.selectedTool}
						toolPaneOpen={workspaceState.toolPaneOpen}
						onToolSelect={onToolSelect}
						emailFrom={emailFrom}
						emailSubject={emailSubject}
						emailBody={emailBody}
						emailMalicious={emailMalicious}
						injectingEmail={injectingEmail}
						sessionId={sessionId}
						injectEmailError={injectEmailError}
						injectEmailResult={injectEmailResult}
						onSubmitEmail={onSubmitEmail}
						onResetEmail={onResetEmail}
						onEmailFromChange={setEmailFrom}
						onEmailSubjectChange={setEmailSubject}
						onEmailBodyChange={setEmailBody}
						onEmailMaliciousChange={setEmailMalicious}
						onTranscriptScroll={onTranscriptScroll}
						showJumpToLatest={showJumpToLatest}
						onJumpToLatest={onJumpToLatest}
						prompt={prompt}
						canSend={canSend}
						onPromptChange={setPrompt}
						onSubmitPrompt={onSubmitPrompt}
						formatTime={formatTime}
					/>
				</section>

				<aside style={{ minHeight: 0, overflowY: "auto" }}>
					{workspaceState.feedbackPanelVisible && (
						<FeedbackColumn
							feedbackLoading={feedbackLoading}
							feedbackError={feedbackError}
							timelineEvents={timelineEvents}
						/>
					)}
				</aside>
			</div>
		</main>
	);
}
