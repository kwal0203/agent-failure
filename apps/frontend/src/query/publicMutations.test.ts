import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as authSession from "../auth/session";
import {
  useRedeemEnrollmentMutation,
  useSubmitPilotRequestMutation,
  useValidateClassCodeMutation,
} from "./publicMutations";
import { createQueryClient } from "./queryClient";

function testWrapper() {
  const queryClient = createQueryClient();
  queryClient.setDefaultOptions({
    queries: { retry: false },
    mutations: { retry: false },
  });
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

describe("public mutations", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("validates a normalized class code and email", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json({
        valid: true,
        enrollmentToken: "enrollment-token",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const mutation = renderHook(() => useValidateClassCodeMutation(), {
      wrapper: testWrapper(),
    });

    const token = await act(() =>
      mutation.result.current.mutateAsync({
        classCode: "  SECURITY-101  ",
        email: "  Learner@Example.edu  ",
      }),
    );

    expect(token).toBe("enrollment-token");
    const request = fetchMock.mock.calls[0]?.[0] as Request;
    expect(request.url).toContain("/api/v1/enrollment/validate-class-code");
    expect(request.method).toBe("POST");
    expect(await request.json()).toEqual({
      classCode: "SECURITY-101",
      email: "learner@example.edu",
    });
  });

  it("redeems an enrollment token with the current authorization", async () => {
    vi.spyOn(authSession, "getCurrentAuthHeader").mockResolvedValue(
      "Bearer test-token",
    );
    const fetchMock = vi
      .fn()
      .mockResolvedValue(Response.json({ enrolled: true }));
    vi.stubGlobal("fetch", fetchMock);
    const mutation = renderHook(() => useRedeemEnrollmentMutation(), {
      wrapper: testWrapper(),
    });

    await act(() => mutation.result.current.mutateAsync("enrollment-token"));

    const request = fetchMock.mock.calls[0]?.[0] as Request;
    expect(request.url).toContain("/api/v1/enrollment/redeem");
    expect(request.method).toBe("POST");
    expect(request.headers.get("Authorization")).toBe("Bearer test-token");
    expect(await request.json()).toEqual({
      enrollmentToken: "enrollment-token",
    });
  });

  it("submits a public pilot request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    const mutation = renderHook(() => useSubmitPilotRequestMutation(), {
      wrapper: testWrapper(),
    });
    const lead = {
      fullName: "Jane Smith",
      workEmail: "jane@example.edu",
      university: "Example University",
    };

    await act(() => mutation.result.current.mutateAsync(lead));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/pilot-request",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(lead),
      }),
    );
  });
});
