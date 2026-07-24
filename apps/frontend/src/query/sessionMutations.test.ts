import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as sessionUi from "../pages/session/ui";
import { createQueryClient } from "./queryClient";
import { sessionMetadataQueryKey } from "./sessionMetadata";
import {
  useInjectSessionEmailMutation,
  useMarkSessionFeedbackSeenMutation,
  useMarkSessionHintsSeenMutation,
  useStopSessionMutation,
} from "./sessionMutations";
import { sessionTraceQueryKey } from "./sessionTrace";

const SESSION_ID = "11111111-1111-1111-1111-111111111111";

function testQueryClient() {
  const queryClient = createQueryClient();
  queryClient.setDefaultOptions({
    queries: { retry: false },
    mutations: { retry: false },
  });
  queryClient.setQueryData(sessionMetadataQueryKey(SESSION_ID), {
    state: "ACTIVE",
  });
  queryClient.setQueryData(sessionTraceQueryKey(SESSION_ID), {
    events: [],
    timelineEvents: [],
  });
  const wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
  return { queryClient, wrapper };
}

function jsonResponse(body: unknown) {
  return Promise.resolve(Response.json(body));
}

describe("session mutations", () => {
  beforeEach(() => {
    vi.spyOn(sessionUi, "getAuthHeader").mockResolvedValue("Bearer test-token");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("stops a session and invalidates metadata and trace", async () => {
    const fetchMock = vi.fn<
      (input: RequestInfo | URL) => ReturnType<typeof jsonResponse>
    >(() => jsonResponse({}));
    vi.stubGlobal("fetch", fetchMock);
    const { queryClient, wrapper } = testQueryClient();
    const mutation = renderHook(() => useStopSessionMutation(SESSION_ID), {
      wrapper,
    });

    await act(() => mutation.result.current.mutateAsync());

    const request = fetchMock.mock.calls[0]?.[0] as Request;
    expect(request.url).toContain(`/api/v1/sessions/${SESSION_ID}/stop`);
    expect(request.method).toBe("POST");
    expect(request.headers.get("Authorization")).toBe("Bearer test-token");
    expect(request.headers.get("Idempotency-Key")).toBe(
      `stop-session:${SESSION_ID}`,
    );
    expect(
      queryClient.getQueryState(sessionMetadataQueryKey(SESSION_ID))
        ?.isInvalidated,
    ).toBe(true);
    expect(
      queryClient.getQueryState(sessionTraceQueryKey(SESSION_ID))
        ?.isInvalidated,
    ).toBe(true);
  });

  it("injects email and invalidates metadata and trace", async () => {
    const fetchMock = vi.fn<
      (
        input: RequestInfo | URL,
        init?: RequestInit,
      ) => ReturnType<typeof jsonResponse>
    >(() =>
      jsonResponse({
        session_id: SESSION_ID,
        email_id: "email-1",
        accepted: true,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const { queryClient, wrapper } = testQueryClient();
    const mutation = renderHook(
      () => useInjectSessionEmailMutation(SESSION_ID),
      { wrapper },
    );

    await act(() =>
      mutation.result.current.mutateAsync({
        emailFrom: "learner@example.com",
        emailSubject: "Incident",
        emailBody: "Please investigate.",
      }),
    );

    const request = fetchMock.mock.calls[0]?.[0] as Request;
    expect(await request.json()).toEqual({
      email_from: "learner@example.com",
      email_subject: "Incident",
      email_body: "Please investigate.",
      source: "learner",
    });
    expect(
      queryClient.getQueryState(sessionMetadataQueryKey(SESSION_ID))
        ?.isInvalidated,
    ).toBe(true);
    expect(
      queryClient.getQueryState(sessionTraceQueryKey(SESSION_ID))
        ?.isInvalidated,
    ).toBe(true);
  });

  it("marks hints as seen and invalidates metadata only", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => jsonResponse({ session_id: SESSION_ID, updated_count: 1 })),
    );
    const { queryClient, wrapper } = testQueryClient();
    const mutation = renderHook(
      () => useMarkSessionHintsSeenMutation(SESSION_ID),
      { wrapper },
    );

    await act(() => mutation.result.current.mutateAsync());

    expect(
      queryClient.getQueryState(sessionMetadataQueryKey(SESSION_ID))
        ?.isInvalidated,
    ).toBe(true);
    expect(
      queryClient.getQueryState(sessionTraceQueryKey(SESSION_ID))
        ?.isInvalidated,
    ).toBe(false);
  });

  it("marks feedback as seen and invalidates metadata only", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => jsonResponse({ session_id: SESSION_ID, updated_count: 1 })),
    );
    const { queryClient, wrapper } = testQueryClient();
    const mutation = renderHook(
      () => useMarkSessionFeedbackSeenMutation(SESSION_ID),
      { wrapper },
    );

    await act(() => mutation.result.current.mutateAsync());

    expect(
      queryClient.getQueryState(sessionMetadataQueryKey(SESSION_ID))
        ?.isInvalidated,
    ).toBe(true);
    expect(
      queryClient.getQueryState(sessionTraceQueryKey(SESSION_ID))
        ?.isInvalidated,
    ).toBe(false);
  });
});
