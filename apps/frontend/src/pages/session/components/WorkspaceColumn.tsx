import type { FormEvent, RefObject } from "react";
import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import type {
  SessionInvoice,
  SessionRuntimeFile,
  SessionTelemetryLog,
  ToolKey,
  TranscriptEntry,
} from "../types";
import { DEMO_H2_STYLE } from "../ui";
import { EmailToolForm } from "./EmailToolForm";

const LAB_2_TOOL_MISUSE_ID = "22222222-2222-2222-2222-222222222222";
const AGENT_LAB_2_TOOL_MISUSE_ID = "55555555-5555-5555-5555-555555555555";
const LAB_3_MEMORY_POISONING_ID = "33333333-3333-3333-3333-333333333333";
const AGENT_LAB_3_MEMORY_POISONING_ID = "66666666-6666-6666-6666-666666666666";

type WorkspaceColumnProps = {
  labId?: string | null;
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
  injectingEmail: boolean;
  sessionId?: string;
  fromValidationError: string | null;
  injectEmailError: string | null;
  injectEmailResult: string | null;
  onSubmitEmail: (e: FormEvent<HTMLFormElement>) => void;
  onResetEmail: () => void;
  onEmailFromChange: (value: string) => void;
  onEmailSubjectChange: (value: string) => void;
  onEmailBodyChange: (value: string) => void;
  onTranscriptScroll: () => void;
  showJumpToLatest: boolean;
  onJumpToLatest: () => void;
  prompt: string;
  canSend: boolean;
  interactionLocked: boolean;
  onPromptChange: (value: string) => void;
  onSubmitPrompt: (e: FormEvent<HTMLFormElement>) => void;
  formatTime: (isoTs: string) => string;
  telemetryLogs: SessionTelemetryLog[];
  invoices: SessionInvoice[];
  runtimeFiles: SessionRuntimeFile[];
};

export function WorkspaceColumn({
  labId,
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
  injectingEmail,
  sessionId,
  fromValidationError,
  injectEmailError,
  injectEmailResult,
  onSubmitEmail,
  onResetEmail,
  onEmailFromChange,
  onEmailSubjectChange,
  onEmailBodyChange,
  onTranscriptScroll,
  showJumpToLatest,
  onJumpToLatest,
  prompt,
  canSend,
  interactionLocked,
  onPromptChange,
  onSubmitPrompt,
  formatTime,
  telemetryLogs,
  invoices,
  runtimeFiles,
}: WorkspaceColumnProps) {
  const [isAttackToolsCollapsed, setIsAttackToolsCollapsed] = useState(false);
  const [isTranscriptCollapsed, setIsTranscriptCollapsed] = useState(false);
  const [logsSeenAtMs, setLogsSeenAtMs] = useState(0);
  const [invoicesSeenAtMs, setInvoicesSeenAtMs] = useState(0);
  const [copiedInvoiceId, setCopiedInvoiceId] = useState<string | null>(null);
  const isLab2Session =
    labId === LAB_2_TOOL_MISUSE_ID || labId === AGENT_LAB_2_TOOL_MISUSE_ID;
  const isAgentLab2Session = labId === AGENT_LAB_2_TOOL_MISUSE_ID;
  const isLab3Session =
    labId === LAB_3_MEMORY_POISONING_ID ||
    labId === AGENT_LAB_3_MEMORY_POISONING_ID;

  const unreadLogCount = useMemo(
    () =>
      telemetryLogs.filter(
        (log) => new Date(log.created_at).getTime() > logsSeenAtMs,
      ).length,
    [logsSeenAtMs, telemetryLogs],
  );
  const hasUnreadLogs = unreadLogCount > 0;
  const unreadInvoiceCount = useMemo(
    () =>
      invoices.filter(
        (invoice) => new Date(invoice.created_at).getTime() > invoicesSeenAtMs,
      ).length,
    [invoices, invoicesSeenAtMs],
  );
  const hasUnreadInvoices = unreadInvoiceCount > 0;

  const tools: Array<{ key: ToolKey; label: string; disabled?: boolean }> = [
    { key: "email", label: "Email", disabled: isAgentLab2Session },
    ...(isLab2Session ? [{ key: "logs" as const, label: "Logs" }] : []),
    ...(isLab3Session ? [{ key: "invoices" as const, label: "Invoices" }] : []),
    { key: "files", label: "Files", disabled: !isLab2Session },
    { key: "payloads", label: "Payloads", disabled: true },
    { key: "notes", label: "Notes", disabled: true },
    { key: "recon", label: "Recon", disabled: true },
  ];

  const paneContent: Record<
    Exclude<ToolKey, "email" | "logs" | "invoices">,
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

  const buildPayInvoiceCommand = (invoice: SessionInvoice): string =>
    [
      "use pay_invoice with:",
      `invoice_id=${invoice.invoice_id}`,
      `vendor_name=${invoice.vendor_name}`,
      "account_number=ACCT-1001",
      `amount=${invoice.amount.toFixed(2)}`,
    ].join("\n");

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
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 8,
          }}
        >
          <h2 style={{ ...DEMO_H2_STYLE, margin: 0 }}>Attack Console</h2>
          <button
            type="button"
            onClick={() => setIsAttackToolsCollapsed((prev) => !prev)}
            aria-label={
              isAttackToolsCollapsed
                ? "Expand attack tools"
                : "Collapse attack tools"
            }
            title={
              isAttackToolsCollapsed
                ? "Expand attack tools"
                : "Collapse attack tools"
            }
            style={{
              border: "1px solid #9bb0c5",
              borderRadius: 6,
              background: "#eef4fa",
              color: "#2a4258",
              padding: "2px 6px",
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 700,
            }}
          >
            {isAttackToolsCollapsed ? "▾" : "▴"}
          </button>
        </div>
        {!isAttackToolsCollapsed ? (
          <div
            style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}
          >
            {tools.map((tool) => {
              const isActive = toolPaneOpen && selectedTool === tool.key;
              const isDisabled = interactionLocked || Boolean(tool.disabled);
              const logsHighlighted = tool.key === "logs" && hasUnreadLogs;
              const invoicesHighlighted =
                tool.key === "invoices" && hasUnreadInvoices;
              const highlighted = logsHighlighted || invoicesHighlighted;

              return (
                <button
                  key={tool.key}
                  type="button"
                  onClick={() => {
                    onToolSelect(tool.key);
                    if (tool.key === "logs") {
                      setLogsSeenAtMs(Date.now());
                    }
                    if (tool.key === "invoices") {
                      setInvoicesSeenAtMs(Date.now());
                    }
                  }}
                  aria-pressed={isActive}
                  disabled={isDisabled}
                  title={`${tool.label} tool`}
                  style={{
                    padding: "6px 10px",
                    borderRadius: 8,
                    border: highlighted
                      ? "1px solid #ff9f1a"
                      : isActive
                        ? "1px solid #4ea4d9"
                        : "1px solid #999",
                    background: highlighted
                      ? "rgba(168, 98, 0, 0.9)"
                      : isActive
                        ? "rgba(26, 76, 107, 0.55)"
                        : "#fff",
                    color: highlighted
                      ? "#fff3df"
                      : isActive
                        ? "#d6f1ff"
                        : "#1f2a33",
                    cursor: isDisabled ? "not-allowed" : "pointer",
                    opacity: isDisabled ? 0.55 : 1,
                    boxShadow: highlighted
                      ? "0 0 0 1px rgba(255, 159, 26, 0.35), 0 0 14px rgba(255, 159, 26, 0.45)"
                      : undefined,
                  }}
                >
                  {tool.label}
                  {tool.key === "logs" && telemetryLogs.length > 0 ? (
                    <span style={{ marginLeft: 6 }}>
                      ({telemetryLogs.length})
                    </span>
                  ) : null}
                  {tool.key === "invoices" && invoices.length > 0 ? (
                    <span style={{ marginLeft: 6 }}>({invoices.length})</span>
                  ) : null}
                </button>
              );
            })}
          </div>
        ) : null}
      </section>

      {toolPaneOpen && !isAttackToolsCollapsed ? (
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
                injectingEmail={injectingEmail}
                sessionId={sessionId}
                fromValidationError={fromValidationError}
                injectEmailError={injectEmailError}
                injectEmailResult={injectEmailResult}
                onSubmitEmail={onSubmitEmail}
                onResetEmail={onResetEmail}
                onEmailFromChange={onEmailFromChange}
                onEmailSubjectChange={onEmailSubjectChange}
                onEmailBodyChange={onEmailBodyChange}
                interactionLocked={interactionLocked}
              />
            </div>
          ) : selectedTool === "logs" ? (
            <div>
              <h3 style={{ marginTop: 0, marginBottom: 8 }}>
                Telemetry Log Feed
              </h3>
              <p
                style={{
                  margin: "0 0 10px 0",
                  fontSize: 13,
                  color: "#263643",
                }}
              >
                Runtime-generated operational errors appear here.
              </p>
              <div
                className="hints-scroll-region"
                style={{
                  border: "1px solid #e1e7ef",
                  borderRadius: 8,
                  maxHeight: 180,
                  overflowY: "auto",
                  padding: 10,
                  background: "#f8fbff",
                }}
              >
                {telemetryLogs.length === 0 ? (
                  <p style={{ margin: 0, color: "#1f2a33" }}>
                    No telemetry reports yet.
                  </p>
                ) : (
                  telemetryLogs
                    .slice()
                    .reverse()
                    .map((log) => (
                      <p
                        key={log.id}
                        style={{
                          margin: "0 0 8px 0",
                          fontSize: 13,
                          color: "#132736",
                        }}
                      >
                        {formatTime(log.created_at)} - {log.message}{" "}
                        <span
                          style={{
                            color: "#1f6d37",
                            fontWeight: 600,
                          }}
                        >
                          [Handled by A-SRE]
                        </span>
                      </p>
                    ))
                )}
              </div>
            </div>
          ) : selectedTool === "invoices" ? (
            <div>
              <h3 style={{ marginTop: 0, marginBottom: 8 }}>
                Incoming Invoice Feed
              </h3>
              <p
                style={{
                  margin: "0 0 10px 0",
                  fontSize: 13,
                  color: "#8ea4b8",
                }}
              >
                Click <strong>Copy pay command</strong> on any invoice, then
                paste into the composer.
              </p>
              <div
                className="hints-scroll-region"
                style={{
                  border: "1px solid #e1e7ef",
                  borderRadius: 8,
                  maxHeight: 180,
                  overflowY: "auto",
                  padding: 10,
                  background: "#f8fbff",
                }}
              >
                {invoices.length === 0 ? (
                  <p style={{ margin: 0, color: "#1f2a33" }}>
                    No incoming invoices yet.
                  </p>
                ) : (
                  invoices
                    .slice()
                    .reverse()
                    .map((invoice) => (
                      <div
                        key={invoice.id}
                        style={{
                          margin: "0 0 10px 0",
                          fontSize: 13,
                          color: "#132736",
                          borderBottom: "1px solid #e7edf4",
                          paddingBottom: 8,
                        }}
                      >
                        <p style={{ margin: "0 0 6px 0" }}>
                          {formatTime(invoice.created_at)} -{" "}
                          {invoice.invoice_id} · {invoice.vendor_name} ·{" "}
                          {invoice.amount.toFixed(2)} {invoice.currency}{" "}
                          {invoice.handled_by ? (
                            <span
                              style={{
                                color: "#1f6d37",
                                fontWeight: 600,
                              }}
                            >
                              [Invoice paid from {invoice.handled_by} to{" "}
                              {invoice.vendor_name} account]
                            </span>
                          ) : (
                            <span
                              style={{
                                color: "#8a5a00",
                                fontWeight: 600,
                              }}
                            >
                              [Pending]
                            </span>
                          )}
                        </p>
                        <button
                          type="button"
                          onClick={() => {
                            void navigator.clipboard.writeText(
                              buildPayInvoiceCommand(invoice),
                            );
                            setCopiedInvoiceId(invoice.id);
                          }}
                          style={{
                            border: "1px solid #9bb0c5",
                            borderRadius: 6,
                            background: "#eef4fa",
                            color: "#2a4258",
                            padding: "3px 8px",
                            cursor: "pointer",
                            fontSize: 12,
                            fontWeight: 600,
                          }}
                        >
                          {copiedInvoiceId === invoice.id
                            ? "Copied"
                            : "Copy pay command"}
                        </button>
                        {copiedInvoiceId === invoice.id ? (
                          <span
                            style={{
                              marginLeft: 8,
                              color: "#2f6f44",
                              fontSize: 12,
                            }}
                          >
                            Paste into composer and send
                          </span>
                        ) : null}
                      </div>
                    ))
                )}
              </div>
            </div>
          ) : selectedTool === "files" && isLab2Session ? (
            <div>
              <h3 style={{ marginTop: 0, marginBottom: 8 }}>Files</h3>
              <p
                style={{
                  margin: "0 0 10px 0",
                  fontSize: 13,
                  color: "#263643",
                }}
              >
                Open trusted runtime artifacts by loading a read prompt into the
                composer.
              </p>
              <div
                className="hints-scroll-region"
                style={{
                  border: "1px solid #e1e7ef",
                  borderRadius: 8,
                  maxHeight: 180,
                  overflowY: "auto",
                  padding: 10,
                  background: "#f8fbff",
                }}
              >
                {runtimeFiles.length === 0 ? (
                  <p style={{ margin: 0, color: "#1f2a33" }}>
                    No files available yet.
                  </p>
                ) : (
                  runtimeFiles.map((file) => (
                    <div
                      key={file.path}
                      style={{
                        margin: "0 0 10px 0",
                        fontSize: 13,
                        color: "#132736",
                        borderBottom: "1px solid #e7edf4",
                        paddingBottom: 8,
                      }}
                    >
                      <p style={{ margin: "0 0 8px 0" }}>
                        <strong>{file.path}</strong>
                      </p>
                      <p
                        style={{
                          margin: "0 0 8px 0",
                          fontSize: 12,
                          color: "#4d6578",
                        }}
                      >
                        Updated {formatTime(file.updated_at)}
                      </p>
                      <pre
                        style={{
                          margin: 0,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          background: "#ffffff",
                          border: "1px solid #d9e4ef",
                          borderRadius: 6,
                          padding: 8,
                          maxHeight: 140,
                          overflowY: "auto",
                        }}
                      >
                        {file.content}
                      </pre>
                    </div>
                  ))
                )}
              </div>
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
        style={{
          border: "1px solid #ddd",
          borderRadius: 8,
          padding: 12,
          marginBottom: 16,
          flex: isTranscriptCollapsed ? "0 0 auto" : "1 1 auto",
          display: "flex",
          flexDirection: "column",
          minHeight: 0,
          overflow: "hidden",
          textAlign: "left",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 8,
            marginBottom: isTranscriptCollapsed ? 0 : 8,
          }}
        >
          <h2 style={{ ...DEMO_H2_STYLE, margin: 0 }}>Transcript</h2>
          <button
            type="button"
            onClick={() => setIsTranscriptCollapsed((prev) => !prev)}
            aria-label={
              isTranscriptCollapsed
                ? "Expand transcript"
                : "Collapse transcript"
            }
            title={
              isTranscriptCollapsed
                ? "Expand transcript"
                : "Collapse transcript"
            }
            style={{
              border: "1px solid #9bb0c5",
              borderRadius: 6,
              background: "#eef4fa",
              color: "#2a4258",
              padding: "2px 6px",
              cursor: "pointer",
              fontSize: 12,
              fontWeight: 700,
            }}
          >
            {isTranscriptCollapsed ? "▾" : "▴"}
          </button>
        </div>
        {!isTranscriptCollapsed ? (
          <div
            className="transcript-scroll-region"
            ref={transcriptViewportRef}
            onScroll={onTranscriptScroll}
            style={{
              flex: "1 1 auto",
              height: 0,
              minHeight: 0,
              overflowY: "auto",
              paddingRight: 2,
            }}
          >
            {transcriptEntries.length === 0 && !activeEntry && (
              <p style={{ margin: 0 }}>
                (streamed agent text will appear here)
              </p>
            )}
            {transcriptEntries.map((entry) => (
              <div
                key={`${entry.timestamp}-${entry.role}-${entry.content.slice(0, 20)}`}
                style={{
                  display: "flex",
                  justifyContent:
                    entry.role === "user" ? "flex-end" : "flex-start",
                  marginTop: 10,
                }}
              >
                <div
                  style={{
                    width: "fit-content",
                    maxWidth: "86%",
                    padding: "10px 12px",
                    borderRadius: 10,
                    border:
                      entry.role === "user"
                        ? "1px solid #2f5f8f"
                        : "1px solid #c6d2dc",
                    background: entry.role === "user" ? "#dcecff" : "#f5f8fb",
                    color: "#102435",
                  }}
                >
                  <p
                    style={{
                      margin: "0 0 6px 0",
                      fontSize: 12,
                      opacity: 0.8,
                    }}
                  >
                    <strong>{entry.role.toUpperCase()}</strong>{" "}
                    {formatTime(entry.timestamp)}
                  </p>
                  <div className="transcript-markdown" style={{ margin: 0 }}>
                    <ReactMarkdown>{entry.content}</ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
            {isAwaitingResponse && !activeEntry && (
              <div style={{ marginTop: 12 }}>
                <p
                  style={{ margin: "8px 0 4px 0", fontSize: 12, opacity: 0.7 }}
                >
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
              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-start",
                  marginTop: 10,
                }}
              >
                <div
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: 10,
                    border: "1px solid #c6d2dc",
                    background: "#f5f8fb",
                    color: "#102435",
                  }}
                >
                  <p
                    style={{
                      margin: "0 0 6px 0",
                      fontSize: 12,
                      opacity: 0.8,
                    }}
                  >
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
          </div>
        ) : (
          <p style={{ margin: 0, fontSize: 12, opacity: 0.7 }}>
            Transcript collapsed
          </p>
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
          white-space: pre-wrap;
        }
        .transcript-markdown p:last-child {
          margin-bottom: 0;
        }
        .transcript-markdown h1,
        .transcript-markdown h2,
        .transcript-markdown h3,
        .transcript-markdown h4,
        .transcript-markdown h5,
        .transcript-markdown h6,
        .transcript-markdown li,
        .transcript-markdown strong,
        .transcript-markdown em,
        .transcript-markdown code {
          color: inherit;
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
          flex: isTranscriptCollapsed ? "1 1 auto" : "0 0 auto",
          minHeight: isTranscriptCollapsed ? 0 : undefined,
          overflow: isTranscriptCollapsed ? "hidden" : undefined,
        }}
      >
        <form
          onSubmit={onSubmitPrompt}
          style={{
            height: isTranscriptCollapsed ? "100%" : undefined,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div
            style={{
              position: "relative",
              flex: isTranscriptCollapsed ? "1 1 auto" : undefined,
              minHeight: isTranscriptCollapsed ? 0 : undefined,
            }}
          >
            <textarea
              rows={isTranscriptCollapsed ? 10 : 4}
              placeholder="Type your prompt..."
              disabled={interactionLocked}
              style={{
                width: "100%",
                boxSizing: "border-box",
                borderRadius: 12,
                border: "1px solid #9eb8cd",
                padding: "10px 48px 10px 12px",
                height: isTranscriptCollapsed ? "100%" : undefined,
                minHeight: isTranscriptCollapsed ? 220 : undefined,
                resize: isTranscriptCollapsed ? "none" : "vertical",
              }}
              value={prompt}
              onChange={(e) => onPromptChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.ctrlKey && e.key === "Enter") {
                  e.preventDefault();
                  e.currentTarget.form?.requestSubmit();
                }
              }}
            />
            <button
              type="submit"
              disabled={!canSend}
              aria-disabled={!canSend}
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
                background: "#1f5f92",
                color: "#ffffff",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                lineHeight: 1,
                cursor: canSend ? "pointer" : "not-allowed",
                opacity: canSend ? 1 : 0.6,
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
