import { useCallback, useEffect, useRef, useState } from "react";

type ConnectionState = "idle" | "connecting" | "open" | "closed" | "error";

type SessionStatusMessage = {
  type: "SESSION_STATUS";
  session_id: string;
  timestamp: string;
  payload: {
    state: string;
    runtime_substate: string | null;
    interactive: boolean;
  };
};

type AgentTextChunkMessage = {
  type: "AGENT_TEXT_CHUNK";
  session_id: string;
  timestamp: string;
  payload: {
    content: string;
    final: boolean;
  };
};

type PolicyDenialMessage = {
  type: "POLICY_DENIAL";
  session_id: string;
  timestamp: string;
  payload: {
    code: string;
    message: string;
  };
};

type SystemErrorMessage = {
  type: "SYSTEM_ERROR";
  session_id: string;
  timestamp: string;
  payload: {
    code: string;
    message: string;
  };
};

type LearnerFeedbackMessage = {
  type: "LEARNER_FEEDBACK";
  session_id: string;
  timestamp: string;
  payload: {
    feedback: Array<{
      status: "learned" | "progress" | "no_progress" | "session_terminal";
      reason_code: string;
      evidence_snippet: string;
    }>;
  };
};

export type ServerMessage =
  | SessionStatusMessage
  | AgentTextChunkMessage
  | PolicyDenialMessage
  | SystemErrorMessage
  | LearnerFeedbackMessage;

export function useSessionStream(sessionId?: string) {
  const [connectionState, setConnectionState] = useState<ConnectionState>("idle");
  const [messages, setMessages] = useState<ServerMessage[]>([]);
  const [reconnectSeq, setReconnectSeq] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    setConnectionState("connecting");
    setMessages([]);

    const token = encodeURIComponent("local:kane:learner");
    const ws = new WebSocket(
      `ws://localhost:8000/api/v1/sessions/${sessionId}/stream?access_token=${token}`,
    );

    wsRef.current = ws;

    ws.onopen = () => {
      // In React StrictMode dev remounts, ignore stale sockets.
      if (wsRef.current !== ws) {
        ws.close();
        return;
      }
      setConnectionState("open");
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data) as ServerMessage;
        setMessages((prev) => [...prev, parsed]);
      } catch {
        // ignore malformed messages for now
      }
    };

    ws.onerror = () => setConnectionState("error");
    ws.onclose = () => setConnectionState("closed");

    return () => {
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
      // Avoid closing while CONNECTING to prevent noisy dev-console warning.
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [sessionId, reconnectSeq]);

  const sendPrompt = useCallback((content: string) => {
    if (!sessionId) return;

    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    ws.send(
      JSON.stringify({
        type: "USER_PROMPT",
        session_id: sessionId,
        timestamp: new Date().toISOString(),
        payload: { content },
      }),
    );
  }, [sessionId]);

  const reconnect = useCallback(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
    setReconnectSeq((prev) => prev + 1);
  }, []);

  return {
    connectionState,
    messages,
    sendPrompt,
    reconnect,
  };
}
