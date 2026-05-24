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
    <div className="flex h-full min-h-0 flex-[1_1_auto] flex-col overflow-hidden">
      <section className="mb-3 flex-none rounded-lg border border-slate-300/90 bg-slate-950/20 p-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="m-0 text-sm font-semibold tracking-wide text-slate-100">
            Attack Console
          </h2>
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
            className="rounded-md border border-slate-400 bg-slate-100 px-1.5 py-0.5 text-xs font-bold text-slate-700"
          >
            {isAttackToolsCollapsed ? "▾" : "▴"}
          </button>
        </div>
        {!isAttackToolsCollapsed ? (
          <div className="mt-2.5 flex flex-wrap gap-2">
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
                  className={`rounded-lg border px-2.5 py-1.5 text-sm ${
                    highlighted
                      ? "border-amber-400 bg-amber-800/90 text-amber-100 shadow-[0_0_0_1px_rgba(251,191,36,0.35),0_0_14px_rgba(251,191,36,0.45)]"
                      : isActive
                        ? "border-sky-400 bg-sky-900/55 text-sky-100"
                        : "border-slate-400 bg-white text-slate-800"
                  } ${isDisabled ? "cursor-not-allowed opacity-55" : "cursor-pointer"}`}
                >
                  {tool.label}
                  {tool.key === "logs" && telemetryLogs.length > 0 ? (
                    <span className="ml-1.5">({telemetryLogs.length})</span>
                  ) : null}
                  {tool.key === "invoices" && invoices.length > 0 ? (
                    <span className="ml-1.5">({invoices.length})</span>
                  ) : null}
                </button>
              );
            })}
          </div>
        ) : null}
      </section>

      {toolPaneOpen && !isAttackToolsCollapsed ? (
        <section className="hints-scroll-region mb-3 max-h-[280px] flex-none overflow-x-hidden overflow-y-auto rounded-lg border border-slate-300/90 bg-slate-950/20 p-4">
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
              <h3 className="mb-2 mt-0 text-base font-semibold text-slate-100">
                Telemetry Log Feed
              </h3>
              <p className="mb-2.5 mt-0 text-sm text-slate-300">
                Runtime-generated operational errors appear here.
              </p>
              <div className="hints-scroll-region max-h-[180px] overflow-y-auto rounded-lg border border-slate-300 bg-slate-50 p-2.5">
                {telemetryLogs.length === 0 ? (
                  <p className="m-0 text-sm text-slate-800">
                    No telemetry reports yet.
                  </p>
                ) : (
                  telemetryLogs
                    .slice()
                    .reverse()
                    .map((log) => (
                      <p
                        key={log.id}
                        className="mb-2 mt-0 text-sm text-slate-900 last:mb-0"
                      >
                        {formatTime(log.created_at)} - {log.message}{" "}
                        <span className="font-semibold text-emerald-700">
                          [Handled by A-SRE]
                        </span>
                      </p>
                    ))
                )}
              </div>
            </div>
          ) : selectedTool === "invoices" ? (
            <div>
              <h3 className="mb-2 mt-0 text-base font-semibold text-slate-100">
                Incoming Invoice Feed
              </h3>
              <p className="mb-2.5 mt-0 text-sm text-slate-300">
                Click <strong>Copy pay command</strong> on any invoice, then
                paste into the composer.
              </p>
              <div className="hints-scroll-region max-h-[180px] overflow-y-auto rounded-lg border border-slate-300 bg-slate-50 p-2.5">
                {invoices.length === 0 ? (
                  <p className="m-0 text-sm text-slate-800">
                    No incoming invoices yet.
                  </p>
                ) : (
                  invoices
                    .slice()
                    .reverse()
                    .map((invoice) => (
                      <div
                        key={invoice.id}
                        className="mb-2.5 border-b border-slate-200 pb-2 text-sm text-slate-900 last:mb-0"
                      >
                        <p className="mb-1.5 mt-0">
                          {formatTime(invoice.created_at)} -{" "}
                          {invoice.invoice_id} · {invoice.vendor_name} ·{" "}
                          {invoice.amount.toFixed(2)} {invoice.currency}{" "}
                          {invoice.handled_by ? (
                            <span className="font-semibold text-emerald-700">
                              [Invoice paid from {invoice.handled_by} to{" "}
                              {invoice.vendor_name} account]
                            </span>
                          ) : (
                            <span className="font-semibold text-amber-700">
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
                          className="cursor-pointer rounded-md border border-slate-400 bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700"
                        >
                          {copiedInvoiceId === invoice.id
                            ? "Copied"
                            : "Copy pay command"}
                        </button>
                        {copiedInvoiceId === invoice.id ? (
                          <span className="ml-2 text-xs text-emerald-700">
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
              <h3 className="mb-2 mt-0 text-base font-semibold text-slate-100">
                Files
              </h3>
              <p className="mb-2.5 mt-0 text-sm text-slate-300">
                Open trusted runtime artifacts by loading a read prompt into the
                composer.
              </p>
              <div className="hints-scroll-region max-h-[180px] overflow-y-auto rounded-lg border border-slate-300 bg-slate-50 p-2.5">
                {runtimeFiles.length === 0 ? (
                  <p className="m-0 text-sm text-slate-800">
                    No files available yet.
                  </p>
                ) : (
                  runtimeFiles.map((file) => (
                    <div
                      key={file.path}
                      className="mb-2.5 border-b border-slate-200 pb-2 text-sm text-slate-900 last:mb-0"
                    >
                      <p className="mb-2 mt-0">
                        <strong>{file.path}</strong>
                      </p>
                      <p className="mb-2 mt-0 text-xs text-slate-600">
                        Updated {formatTime(file.updated_at)}
                      </p>
                      <pre className="m-0 max-h-[140px] overflow-y-auto whitespace-pre-wrap break-words rounded-md border border-slate-300 bg-white p-2">
                        {file.content}
                      </pre>
                    </div>
                  ))
                )}
              </div>
            </div>
          ) : selectedTool ? (
            <div>
              <h3 className="mb-2 mt-0 text-base font-semibold text-slate-100">
                {paneContent[selectedTool].title}
              </h3>
              <p className="m-0 text-sm text-slate-300">
                {paneContent[selectedTool].description}
              </p>
            </div>
          ) : null}
        </section>
      ) : null}

      <section
        className="mb-4 flex min-h-0 flex-col overflow-hidden rounded-lg border border-slate-300/90 bg-slate-950/20 p-3 text-left"
        style={{ flex: isTranscriptCollapsed ? "0 0 auto" : "1 1 auto" }}
      >
        <div
          className="flex items-center justify-between gap-2"
          style={{ marginBottom: isTranscriptCollapsed ? 0 : 8 }}
        >
          <h2 className="m-0 text-sm font-semibold tracking-wide text-slate-100">
            Transcript
          </h2>
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
            className="rounded-md border border-slate-400 bg-slate-100 px-1.5 py-0.5 text-xs font-bold text-slate-700"
          >
            {isTranscriptCollapsed ? "▾" : "▴"}
          </button>
        </div>
        {!isTranscriptCollapsed ? (
          <div
            ref={transcriptViewportRef}
            onScroll={onTranscriptScroll}
            className="transcript-scroll-region h-0 min-h-0 flex-[1_1_auto] overflow-y-auto pb-2 pr-0.5"
          >
            {transcriptEntries.length === 0 && !activeEntry && (
              <p className="m-0 text-slate-300/85">
                (streamed agent text will appear here)
              </p>
            )}
            {transcriptEntries.map((entry) => (
              <div
                key={`${entry.timestamp}-${entry.role}-${entry.content.slice(0, 20)}`}
                className={`mt-2.5 flex border px-3 py-2.5 ${
                  entry.role === "user"
                    ? "border-sky-700 bg-sky-950/60 text-sky-100"
                    : "border-rose-700 bg-rose-950/60 text-rose-100"
                }`}
              >
                <div className="flex w-full min-w-0 flex-col items-start text-left">
                  <p className="mb-1.5 mt-0 text-xs opacity-80">
                    <strong>{entry.role.toUpperCase()}</strong>{" "}
                    {formatTime(entry.timestamp)}
                  </p>
                  <div className="transcript-markdown m-0">
                    <ReactMarkdown>{entry.content}</ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
            {isAwaitingResponse && !activeEntry && (
              <div className="mt-3">
                <p className="mb-1 mt-2 text-xs opacity-70">
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
              <div className="mt-2.5 flex border border-rose-700 bg-rose-950/60 px-3 py-2.5 text-rose-100">
                <div className="flex w-full min-w-0 flex-col">
                  <p className="mb-1.5 mt-0 text-xs opacity-80">
                    <strong>AGENT</strong> streaming...
                  </p>
                  <span className="break-words whitespace-pre-wrap leading-relaxed [overflow-wrap:anywhere]">
                    {activeEntry}
                  </span>
                </div>
              </div>
            )}
            {showJumpToLatest && (
              <div className="sticky bottom-2 mt-3 flex justify-end">
                <button
                  type="button"
                  onClick={onJumpToLatest}
                  className="rounded-lg border border-slate-400 bg-white px-2.5 py-1 text-xs font-semibold text-slate-800 hover:bg-slate-100"
                >
                  Jump to latest
                </button>
              </div>
            )}
          </div>
        ) : (
          <p className="m-0 text-xs opacity-70">Transcript collapsed</p>
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
          overflow-wrap: anywhere;
          word-break: break-word;
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
        className="rounded-lg border border-slate-300/90 bg-slate-950/20 p-3"
        style={{
          flex: isTranscriptCollapsed ? "1 1 auto" : "0 0 auto",
          minHeight: isTranscriptCollapsed ? 0 : undefined,
          overflow: isTranscriptCollapsed ? "hidden" : undefined,
        }}
      >
        <form
          onSubmit={onSubmitPrompt}
          className="flex flex-col"
          style={{ height: isTranscriptCollapsed ? "100%" : undefined }}
        >
          <div
            className="relative"
            style={{
              flex: isTranscriptCollapsed ? "1 1 auto" : undefined,
              minHeight: isTranscriptCollapsed ? 0 : undefined,
            }}
          >
            <textarea
              rows={isTranscriptCollapsed ? 10 : 4}
              placeholder="Type your prompt..."
              disabled={interactionLocked}
              className="w-full rounded-xl border border-slate-400/70 bg-black/35 px-3 py-2.5 pr-12 text-slate-100 outline-none placeholder:text-slate-500"
              style={{
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
              className="absolute bottom-2.5 right-2.5 inline-flex h-8 w-8 items-center justify-center rounded-full border border-sky-700 bg-sky-800 font-bold leading-none text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              ↑
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
