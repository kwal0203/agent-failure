import { useCallback, useEffect, useRef, useState } from "react";
import type { ServerMessage } from "../../../contracts/ts/index";
import { getCurrentAccessToken } from "../auth/context";

export type { ServerMessage } from "../../../contracts/ts/index";

type ConnectionState = "idle" | "connecting" | "open" | "closed" | "error";

export function useSessionStream(sessionId?: string) {
  const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const wsBase = apiBase.replace(/^http/i, "ws");
  const [connectionState, setConnectionState] =
    useState<ConnectionState>("idle");
  const [messages, setMessages] = useState<ServerMessage[]>([]);
  const [reconnectSeq, setReconnectSeq] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    const resetTimer = window.setTimeout(() => {
      setConnectionState("connecting");
      setMessages([]);
    }, 0);

    const token = encodeURIComponent(getCurrentAccessToken());
    const ws = new WebSocket(
      `${wsBase}/api/v1/sessions/${sessionId}/stream?access_token=${token}&reconnect_seq=${reconnectSeq}`,
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
      if (wsRef.current !== ws) return;
      try {
        const parsed = JSON.parse(event.data) as ServerMessage;
        setMessages((prev) => [...prev, parsed]);
      } catch {
        // ignore malformed messages for now
      }
    };

    ws.onerror = () => {
      if (wsRef.current !== ws) return;
      setConnectionState("error");
    };
    ws.onclose = () => {
      if (wsRef.current !== ws) return;
      setConnectionState("closed");
    };

    return () => {
      window.clearTimeout(resetTimer);
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
      // Avoid closing while CONNECTING to prevent noisy dev-console warning.
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, [reconnectSeq, sessionId, wsBase]);

  const sendPrompt = useCallback(
    (content: string) => {
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
    },
    [sessionId],
  );

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
