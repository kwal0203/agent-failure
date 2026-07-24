import { useCallback, useMemo, useRef, useState } from "react";
import useWebSocket, {
  ReadyState,
  type Options as WebSocketOptions,
} from "react-use-websocket";
import type { ServerMessage } from "../../../contracts/ts/index";
import { getCurrentAccessToken } from "../auth/session";
import { getApiBaseUrl } from "../config";

export type { ServerMessage } from "../../../contracts/ts/index";

type ConnectionState = "idle" | "connecting" | "open" | "closed" | "error";

const MAX_RECONNECT_ATTEMPTS = 5;
const MAX_RECONNECT_DELAY_MS = 30_000;

function reconnectDelay(attemptNumber: number): number {
  return Math.min(1_000 * 2 ** attemptNumber, MAX_RECONNECT_DELAY_MS);
}

function shouldReconnect(event: CloseEvent): boolean {
  // A normal close is intentional. Policy violations commonly mean that
  // authentication or authorization failed and retrying the same request
  // would only create noise.
  return event.code !== 1000 && event.code !== 1008;
}

export function useSessionStream(sessionId?: string) {
  const apiBase = getApiBaseUrl();
  const wsBase = apiBase.replace(/^http/i, "ws");
  const [reconnectNonce, setReconnectNonce] = useState(0);
  const streamKey = `${sessionId ?? "idle"}:${reconnectNonce}`;
  const [messageState, setMessageState] = useState<{
    streamKey: string;
    messages: ServerMessage[];
  }>({ streamKey, messages: [] });
  const [connectionErrorState, setConnectionErrorState] = useState<{
    streamKey: string;
    failed: boolean;
  }>({ streamKey, failed: false });
  const reconnectSequenceRef = useRef({
    sessionId,
    next: 0,
  });

  const getSocketUrl = useCallback(async () => {
    if (!sessionId) {
      throw new Error("Cannot connect a session stream without a session ID.");
    }
    if (reconnectSequenceRef.current.sessionId !== sessionId) {
      reconnectSequenceRef.current = { sessionId, next: 0 };
    }

    // Amplify refreshes an expired Cognito session while resolving this call.
    // react-use-websocket invokes the URL factory again for every retry, so a
    // reconnect never has to reuse the token embedded in the previous URL.
    const token = encodeURIComponent(await getCurrentAccessToken());
    const reconnectSequence = Math.max(
      reconnectSequenceRef.current.next,
      reconnectNonce,
    );
    reconnectSequenceRef.current.next = reconnectSequence + 1;

    return `${wsBase}/api/v1/sessions/${sessionId}/stream?access_token=${token}&reconnect_seq=${reconnectSequence}`;
  }, [reconnectNonce, sessionId, wsBase]);

  const options = useMemo<WebSocketOptions>(
    () => ({
      onOpen: () => setConnectionErrorState({ streamKey, failed: false }),
      onMessage: (event) => {
        try {
          const parsed = JSON.parse(String(event.data)) as ServerMessage;
          setMessageState((previous) => ({
            streamKey,
            messages:
              previous.streamKey === streamKey
                ? [...previous.messages, parsed]
                : [parsed],
          }));
        } catch {
          // Malformed protocol messages are ignored so one bad frame does not
          // interrupt the rest of the live session.
        }
      },
      onError: () => setConnectionErrorState({ streamKey, failed: true }),
      onClose: (event) => {
        if (shouldReconnect(event)) {
          setConnectionErrorState({ streamKey, failed: true });
        }
      },
      onReconnectStop: () =>
        setConnectionErrorState({ streamKey, failed: true }),
      shouldReconnect,
      reconnectAttempts: MAX_RECONNECT_ATTEMPTS,
      reconnectInterval: reconnectDelay,
      // This also retries a transient failure while Amplify is obtaining or
      // refreshing the access token used by the asynchronous URL factory.
      retryOnError: true,
    }),
    [streamKey],
  );

  const { readyState, sendJsonMessage } = useWebSocket(
    sessionId ? getSocketUrl : null,
    options,
  );

  const messages =
    messageState.streamKey === streamKey ? messageState.messages : [];
  const connectionError =
    connectionErrorState.streamKey === streamKey && connectionErrorState.failed;

  const connectionState = useMemo<ConnectionState>(() => {
    if (!sessionId) return "idle";
    if (readyState === ReadyState.OPEN) return "open";
    if (
      readyState === ReadyState.CONNECTING ||
      readyState === ReadyState.UNINSTANTIATED
    ) {
      return "connecting";
    }
    if (connectionError) return "error";
    return "closed";
  }, [connectionError, readyState, sessionId]);

  const sendPrompt = useCallback(
    (content: string) => {
      if (!sessionId || readyState !== ReadyState.OPEN) return;

      sendJsonMessage(
        {
          type: "USER_PROMPT",
          session_id: sessionId,
          timestamp: new Date().toISOString(),
          payload: { content },
        },
        false,
      );
    },
    [readyState, sendJsonMessage, sessionId],
  );

  const reconnect = useCallback(() => {
    setReconnectNonce((previous) => previous + 1);
  }, []);

  return {
    connectionState,
    messages,
    sendPrompt,
    reconnect,
  };
}
