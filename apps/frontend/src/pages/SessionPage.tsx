import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
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

const API_BASE = "http://localhost:8000";
const AUTH_HEADER = "Bearer local:kane:learner";

export default function SessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { connectionState, messages, sendPrompt, reconnect } =
    useSessionStream(sessionId);
  const processedMessageCount = useRef(0);
  const transcriptViewportRef = useRef<HTMLDivElement | null>(null);
  const activeEntryTsRef = useRef<string | null>(null);
  const displayedEntryRef = useRef("");
  const pendingBufferRef = useRef("");
  const finalizePendingRef = useRef(false);
  const animationFrameRef = useRef<number | null>(null);
  const lastRevealAtMsRef = useRef(0);
  const [metadata, setMetadata] = useState<SessionMetadata | null>(null);
  const [metadataError, setMetadataError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [transcriptEntries, setTranscriptEntries] = useState<TranscriptEntry[]>([]);
  const [activeEntry, setActiveEntry] = useState("");
  const [isAwaitingResponse, setIsAwaitingResponse] = useState(false);

  const resetActiveStream = () => {
    displayedEntryRef.current = "";
    pendingBufferRef.current = "";
    finalizePendingRef.current = false;
    activeEntryTsRef.current = null;
    setActiveEntry("");
    if (animationFrameRef.current !== null) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
  };

  const drainRevealFrame = () => {
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
            last.timestamp === (activeEntryTsRef.current ?? new Date().toISOString())
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
  };

  const ensureRevealLoop = () => {
    if (animationFrameRef.current === null) {
      animationFrameRef.current = requestAnimationFrame(drainRevealFrame);
    }
  };

  useEffect(() => {
    if (!sessionId) return;

    const run = async () => {
      setLoading(true);
      setMetadataError(null);

      try {
        const res = await fetch(`${API_BASE}/api/v1/sessions/${sessionId}`, {
          method: "GET",
          headers: {
            Authorization: AUTH_HEADER,
            "Content-Type": "application/json",
          },
        });

        if (!res.ok) {
          setMetadataError(`HTTP ${res.status}`);
          return;
        }

        const data = (await res.json()) as GetSessionMetadataResponse;
        setMetadata(data.session);
      } catch (e) {
        setMetadataError(e instanceof Error ? e.message : "request failed");
      } finally {
        setLoading(false);
      }
    };

    void run();
  }, [sessionId]);

  useEffect(() => {
    if (processedMessageCount.current > messages.length) {
      processedMessageCount.current = 0;
    }

    const newMessages = messages.slice(processedMessageCount.current);
    if (newMessages.length == 0) return;

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
      }
    }

    processedMessageCount.current = messages.length;
  }, [messages]);

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

  useEffect(() => {
    const viewport = transcriptViewportRef.current;
    if (!viewport) return;
    viewport.scrollTop = viewport.scrollHeight;
  }, [activeEntry, transcriptEntries.length]);

  useEffect(() => {
    return () => {
      if (animationFrameRef.current !== null) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return (
    <main style={{ maxWidth: 960, margin: "0 auto", padding: "24px" }}>
      <header style={{ marginBottom: "16px" }}>
        <h1>Session</h1>
        <p>
          <strong>session_id:</strong> {sessionId ?? "missing"}
        </p>
        <p>
          <strong>WebSocket:</strong> {connectionState}
        </p>
        {(connectionState === "closed" || connectionState === "error") && (
          <button type="button" onClick={reconnect}>
            Reconnect
          </button>
        )}
      </header>

      <section
        style={{
          border: "1px solid #ddd",
          borderRadius: 8,
          padding: 16,
          marginBottom: 16,
        }}
      >
        <h2>Status</h2>
        {loading && <p>Loading...</p>}
        {metadataError && <p style={{ color: "red" }}>Error: {metadataError}</p>}
        {metadata && (
          <>
            <p>State: {metadata.state}</p>
            <p>Runtime substate: {metadata.runtime_substate ?? "-"}</p>
            <p>Interactive: {String(metadata.interactive)}</p>
          </>
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
        <h2>Transcript</h2>
        {transcriptEntries.length === 0 && !activeEntry && (
          <p style={{ margin: 0 }}>(streamed agent text will appear here)</p>
        )}
        {transcriptEntries.map((entry, index) => (
          <div key={`${index}-${entry.content.slice(0, 20)}`}>
            <p style={{ margin: "8px 0 4px 0", fontSize: 12, opacity: 0.7 }}>
              <strong>{entry.role.toUpperCase()}</strong> {formatTime(entry.timestamp)}
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
              {activeTokens.map((token, index) => (
                <span
                  key={`${index}-${token}`}
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
              ))}
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
        <h2>Prompt</h2>
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
              Prompt disabled: socket must be open, session interactive, and no turn in progress.
            </p>
          )}
        </form>
      </section>
    </main>
  );
}
