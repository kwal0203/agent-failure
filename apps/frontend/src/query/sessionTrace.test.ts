import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as sessionUi from "../pages/session/ui";
import { createQueryClient } from "./queryClient";
import {
  getSessionTrace,
  getSessionTraceRefetchInterval,
  sessionTraceQueryKey,
  useSessionTraceQuery,
} from "./sessionTrace";

describe("session trace query", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("uses a cache key scoped to the session", () => {
    expect(
      sessionTraceQueryKey("11111111-1111-1111-1111-111111111111"),
    ).toEqual(["sessions", "11111111-1111-1111-1111-111111111111", "trace"]);
  });

  it("continues polling while the session is active", () => {
    vi.spyOn(Math, "random").mockReturnValue(0.5);

    expect(getSessionTraceRefetchInterval(true)).toBe(1000);
  });

  it("continues polling until session metadata is available", () => {
    vi.spyOn(Math, "random").mockReturnValue(0.5);

    expect(getSessionTraceRefetchInterval()).toBe(1000);
  });

  it("stops polling once the session reaches a terminal state", () => {
    expect(getSessionTraceRefetchInterval(false)).toBe(false);
  });

  it("normalizes events and maps the shared timeline representation", async () => {
    vi.spyOn(sessionUi, "getAuthHeader").mockResolvedValue("Bearer test-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json({
          events: [
            {
              id: "evt-a",
              occurred_at: "2026-07-23T12:00:00Z",
              family: "learner",
              event_type: "TOKEN_DISCLOSED",
              payload: {},
              report_selectable: true,
              evidence_type: "exploit_outcome",
              objective_keys: ["lab1.secret_disclosure"],
              why_it_matters: "Secret exposure",
              default_priority: "high",
            },
          ],
          next_cursor: null,
        }),
      ),
    );

    const trace = await getSessionTrace("11111111-1111-1111-1111-111111111111");

    expect(trace.events).toHaveLength(1);
    expect(trace.timelineEvents).toHaveLength(1);
    expect(trace.timelineEvents[0]).toMatchObject({
      id: "trace-evt-a",
      title: "Token disclosed",
      report_selectable: true,
    });
  });

  it("shares one cached request across multiple consumers", async () => {
    vi.spyOn(sessionUi, "getAuthHeader").mockResolvedValue("Bearer test-token");
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.endsWith("/trace")) {
        return Promise.resolve(
          Response.json({ events: [], next_cursor: null }),
        );
      }
      return Promise.resolve(
        Response.json({ session: { state: "COMPLETED" } }),
      );
    });
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = createQueryClient();
    queryClient.setDefaultOptions({
      queries: { retry: false },
      mutations: { retry: false },
    });
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children);

    const first = renderHook(() => useSessionTraceQuery("shared-session"), {
      wrapper,
    });
    const second = renderHook(() => useSessionTraceQuery("shared-session"), {
      wrapper,
    });

    await waitFor(() => {
      expect(first.result.current.isSuccess).toBe(true);
      expect(second.result.current.isSuccess).toBe(true);
    });
    expect(
      fetchMock.mock.calls.filter(([input]) =>
        (input instanceof Request ? input.url : String(input)).endsWith(
          "/trace",
        ),
      ),
    ).toHaveLength(1);
  });
});
