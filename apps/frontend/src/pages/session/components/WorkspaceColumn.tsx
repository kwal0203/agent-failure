import type { FormEvent, RefObject } from "react";
import ReactMarkdown from "react-markdown";
import type { TranscriptEntry } from "../types";
import { DEMO_H2_STYLE } from "../ui";

type WorkspaceColumnProps = {
	transcriptViewportRef: RefObject<HTMLDivElement | null>;
	transcriptEntries: TranscriptEntry[];
	activeEntry: string;
	activeTokens: string[];
	isAwaitingResponse: boolean;
	prompt: string;
	canSend: boolean;
	onPromptChange: (value: string) => void;
	onSubmitPrompt: (e: FormEvent<HTMLFormElement>) => void;
	formatTime: (isoTs: string) => string;
};

export function WorkspaceColumn({
	transcriptViewportRef,
	transcriptEntries,
	activeEntry,
	activeTokens,
	isAwaitingResponse,
	prompt,
	canSend,
	onPromptChange,
	onSubmitPrompt,
	formatTime,
}: WorkspaceColumnProps) {
	return (
		<>
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
						onChange={(e) => onPromptChange(e.target.value)}
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
		</>
	);
}
