import { act, renderHook } from "@testing-library/react";
import useWebSocket, {
  ReadyState,
  type Options as WebSocketOptions,
} from "react-use-websocket";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getCurrentAccessToken } from "../auth/session";
import { useSessionStream } from "./useSessionStream";

vi.mock("react-use-websocket", () => ({
  default: vi.fn(),
  ReadyState: {
    UNINSTANTIATED: -1,
    CONNECTING: 0,
    OPEN: 1,
    CLOSING: 2,
    CLOSED: 3,
  },
}));

vi.mock("../auth/session", () => ({
  getCurrentAccessToken: vi.fn(),
}));

const SESSION_ID = "11111111-1111-1111-1111-111111111111";
const sendJsonMessage = vi.fn();

function mockSocketState(readyState: ReadyState) {
  vi.mocked(useWebSocket).mockReturnValue({
    sendMessage: vi.fn(),
    sendJsonMessage,
    lastMessage: null,
    lastJsonMessage: null,
    readyState,
    getWebSocket: vi.fn(() => null),
  });
}

function latestSocketCall() {
  const call = vi.mocked(useWebSocket).mock.calls.at(-1);
  if (!call) {
    throw new Error("Expected useWebSocket to be called.");
  }
  return {
    url: call[0],
    options: call[1] as WebSocketOptions,
  };
}

describe("useSessionStream", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSocketState(ReadyState.OPEN);
    vi.mocked(getCurrentAccessToken).mockResolvedValue("token-1");
  });

  it("gets a fresh access token and sequence for every connection attempt", async () => {
    vi.mocked(getCurrentAccessToken)
      .mockResolvedValueOnce("token one")
      .mockResolvedValueOnce("token two");
    renderHook(() => useSessionStream(SESSION_ID));

    const { url } = latestSocketCall();
    expect(typeof url).toBe("function");
    if (typeof url !== "function") return;

    await expect(url()).resolves.toContain(
      `/${SESSION_ID}/stream?access_token=token%20one&reconnect_seq=0`,
    );
    await expect(url()).resolves.toContain(
      `/${SESSION_ID}/stream?access_token=token%20two&reconnect_seq=1`,
    );
    expect(getCurrentAccessToken).toHaveBeenCalledTimes(2);
  });

  it("preserves the hook API while delegating JSON sends to the library", () => {
    const { result } = renderHook(() => useSessionStream(SESSION_ID));

    act(() => result.current.sendPrompt("Investigate the alert"));

    expect(sendJsonMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "USER_PROMPT",
        session_id: SESSION_ID,
        payload: { content: "Investigate the alert" },
      }),
      false,
    );
  });

  it("does not queue prompts while the socket is disconnected", () => {
    mockSocketState(ReadyState.CLOSED);
    const { result } = renderHook(() => useSessionStream(SESSION_ID));

    act(() => result.current.sendPrompt("Do not queue this"));

    expect(sendJsonMessage).not.toHaveBeenCalled();
  });

  it("collects valid protocol messages and ignores malformed frames", () => {
    const { result } = renderHook(() => useSessionStream(SESSION_ID));
    const { options } = latestSocketCall();
    const message = {
      type: "SESSION_STATUS",
      session_id: SESSION_ID,
      timestamp: "2026-07-23T12:00:00Z",
      payload: { state: "ACTIVE" },
    };

    act(() => {
      options.onMessage?.(
        new MessageEvent("message", { data: JSON.stringify(message) }),
      );
      options.onMessage?.(new MessageEvent("message", { data: "not-json" }));
    });

    expect(result.current.messages).toEqual([message]);
  });

  it("uses bounded exponential backoff only for unexpected closures", () => {
    renderHook(() => useSessionStream(SESSION_ID));
    const { options } = latestSocketCall();
    const delay = options.reconnectInterval;

    expect(options.reconnectAttempts).toBe(5);
    expect(options.retryOnError).toBe(true);
    expect(
      options.shouldReconnect?.(new CloseEvent("close", { code: 1006 })),
    ).toBe(true);
    expect(
      options.shouldReconnect?.(new CloseEvent("close", { code: 1000 })),
    ).toBe(false);
    expect(
      options.shouldReconnect?.(new CloseEvent("close", { code: 1008 })),
    ).toBe(false);
    expect(typeof delay).toBe("function");
    if (typeof delay !== "function") return;
    expect(delay(0)).toBe(1_000);
    expect(delay(4)).toBe(16_000);
    expect(delay(10)).toBe(30_000);
  });

  it("forces a fresh library connection when reconnect is requested", async () => {
    const { result } = renderHook(() => useSessionStream(SESSION_ID));
    const firstUrl = latestSocketCall().url;
    if (typeof firstUrl !== "function") {
      throw new Error("Expected an asynchronous URL factory.");
    }
    await firstUrl();

    act(() => result.current.reconnect());

    const secondUrl = latestSocketCall().url;
    expect(secondUrl).not.toBe(firstUrl);
    if (typeof secondUrl !== "function") {
      throw new Error("Expected an asynchronous URL factory.");
    }
    await expect(secondUrl()).resolves.toContain("reconnect_seq=1");
    expect(getCurrentAccessToken).toHaveBeenCalledTimes(2);
  });
});
