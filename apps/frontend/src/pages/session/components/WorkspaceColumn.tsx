import type { FormEvent, RefObject } from "react";
import ReactMarkdown from "react-markdown";
import type { ToolKey, TranscriptEntry } from "../types";
import { DEMO_H2_STYLE } from "../ui";
import { EmailToolForm } from "./EmailToolForm";

type WorkspaceColumnProps = {
  transcriptViewportRef: RefObject<HTMLDivElement | null>;
  transcriptEntries: TranscriptEntry[];
  activeEntry: string;
  activeTokens: string[];
  isAwaitingResponse: boolean;
  selectedTool: ToolKey | null;
  toolPaneOpen: boolean;
  onToolSelect: (tool: ToolKey) => void;
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
  onTranscriptScroll: () => void;
  showJumpToLatest: boolean;
  onJumpToLatest: () => void;
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
  selectedTool,
  toolPaneOpen,
  onToolSelect,
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
  onTranscriptScroll,
  showJumpToLatest,
  onJumpToLatest,
  prompt,
  canSend,
  onPromptChange,
  onSubmitPrompt,
  formatTime,
}: WorkspaceColumnProps) {
  const tools: Array<{ key: ToolKey; label: string }> = [
    { key: "email", label: "Email" },
    { key: "files", label: "Files" },
    { key: "payloads", label: "Payloads" },
    { key: "notes", label: "Notes" },
    { key: "recon", label: "Recon" },
  ];

  const paneContent: Record<
    Exclude<ToolKey, "email">,
    { title: string; description: string }
  > = {
    files: {
      title: "Files Tool Panel",
      description: "Review or stage supporting artifacts for attack planning.",
    },
    payloads: {
      title: "Payloads Tool Panel",
      description:
        "Draft and iterate reusable prompt-injection payload variants.",
    },
    notes: {
      title: "Notes Tool Panel",
      description: "Track hypotheses, failed attempts, and observed behavior.",
    },
    recon: {
      title: "Recon Tool Panel",
      description: "Collect context signals before crafting exploit messages.",
    },
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        flex: "1 1 auto",
        height: "100%",
        minHeight: 0,
        overflow: "hidden",
      }}
    >
      <section
        style={{
          border: "1px solid #ddd",
          borderRadius: 8,
          padding: 12,
          marginBottom: 12,
          flex: "0 0 auto",
        }}
      >
        <h2 style={{ ...DEMO_H2_STYLE, margin: "0 0 10px 0" }}>Attack Tools</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {tools.map((tool) => {
            const isActive = toolPaneOpen && selectedTool === tool.key;
            return (
              <button
                key={tool.key}
                type="button"
                onClick={() => onToolSelect(tool.key)}
                aria-pressed={isActive}
                title={`${tool.label} tool`}
                style={{
                  padding: "6px 10px",
                  borderRadius: 8,
                  border: isActive ? "1px solid #4ea4d9" : "1px solid #999",
                  background: isActive ? "rgba(26, 76, 107, 0.55)" : "#fff",
                  color: isActive ? "#d6f1ff" : "#1f2a33",
                  cursor: "pointer",
                }}
              >
                {tool.label}
              </button>
            );
          })}
        </div>
      </section>

      {toolPaneOpen ? (
        <section
          style={{
            border: "1px solid #ddd",
            borderRadius: 8,
            padding: 16,
            marginBottom: 12,
            flex: "0 0 auto",
            maxHeight: 280,
            overflowY: "auto",
            overflowX: "hidden",
          }}
        >
          {selectedTool === "email" ? (
            <div>
              <EmailToolForm
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
                onEmailFromChange={onEmailFromChange}
                onEmailSubjectChange={onEmailSubjectChange}
                onEmailBodyChange={onEmailBodyChange}
                onEmailMaliciousChange={onEmailMaliciousChange}
              />
            </div>
          ) : selectedTool ? (
            <div>
              <h3 style={{ marginTop: 0, marginBottom: 8 }}>
                {paneContent[selectedTool].title}
              </h3>
              <p style={{ margin: 0 }}>
                {paneContent[selectedTool].description}
              </p>
            </div>
          ) : null}
        </section>
      ) : null}

      <section
        className="transcript-scroll-region"
        ref={transcriptViewportRef}
        onScroll={onTranscriptScroll}
        style={{
          border: "1px solid #ddd",
          borderRadius: 8,
          padding: 16,
          marginBottom: 16,
          flex: "1 1 auto",
          height: 0,
          minHeight: 0,
          overflowY: "auto",
          textAlign: "left",
        }}
      >
        <h2 style={DEMO_H2_STYLE}>Transcript</h2>
        {transcriptEntries.length === 0 && !activeEntry && (
          <p style={{ margin: 0 }}>(streamed agent text will appear here)</p>
        )}
        {transcriptEntries.map((entry) => (
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
        {showJumpToLatest && (
          <div
            style={{
              position: "sticky",
              bottom: 8,
              display: "flex",
              justifyContent: "flex-end",
              marginTop: 12,
            }}
          >
            <button type="button" onClick={onJumpToLatest}>
              Jump to latest
            </button>
          </div>
        )}
      </section>

      <style>{`
        @keyframes wordIn {
          from { opacity: 0; transform: translateX(6px); }
          to { opacity: 1; transform: translateX(0); }
        }
        .transcript-scroll-region {
          scrollbar-width: thin;
          scrollbar-color: #88a2b8 transparent;
        }
        .transcript-scroll-region::-webkit-scrollbar {
          width: 10px;
        }
        .transcript-scroll-region::-webkit-scrollbar-track {
          background: transparent;
        }
        .transcript-scroll-region::-webkit-scrollbar-thumb {
          background-color: #88a2b8;
          border-radius: 999px;
          border: 2px solid transparent;
          background-clip: content-box;
        }
        .transcript-scroll-region::-webkit-scrollbar-thumb:hover {
          background-color: #6f8ea8;
        }
        .transcript-markdown p {
          margin: 0 0 0.5em 0;
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
        style={{
          border: "1px solid #ddd",
          borderRadius: 8,
          padding: 12,
          flex: "0 0 auto",
        }}
      >
        <form onSubmit={onSubmitPrompt}>
          <div style={{ position: "relative" }}>
            <textarea
              rows={4}
              placeholder="Type your prompt..."
              style={{
                width: "100%",
                boxSizing: "border-box",
                borderRadius: 12,
                border: "1px solid #9eb8cd",
                padding: "10px 48px 10px 12px",
                resize: "vertical",
              }}
              value={prompt}
              onChange={(e) => onPromptChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.ctrlKey && e.key === "Enter") {
                  e.preventDefault();
                  e.currentTarget.form?.requestSubmit();
                }
              }}
              disabled={!canSend}
            />
            <button
              type="submit"
              disabled={!canSend}
              aria-label="Send prompt"
              title="Send"
              style={{
                position: "absolute",
                right: 10,
                bottom: 10,
                width: 30,
                height: 30,
                borderRadius: "50%",
                border: "1px solid #2f6ea1",
                background: canSend ? "#1f5f92" : "#8fa5b6",
                color: "#ffffff",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                lineHeight: 1,
                cursor: canSend ? "pointer" : "not-allowed",
              }}
            >
              ↑
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
