import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as sessionUi from "../pages/session/ui";
import { createQueryClient } from "./queryClient";
import {
  createReportDraftSnapshot,
  getSessionReportDraft,
  sessionReportDraftQueryKey,
  useSaveSessionReportDraftMutation,
  useSessionReportDraftQuery,
} from "./sessionReportDraft";

const SESSION_ID = "11111111-1111-1111-1111-111111111111";

describe("session report draft query", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("uses a cache key scoped to the session", () => {
    expect(sessionReportDraftQueryKey(SESSION_ID)).toEqual([
      "sessions",
      SESSION_ID,
      "report-draft",
    ]);
  });

  it("normalizes sections, evidence selection, assignments, and snapshot", async () => {
    vi.spyOn(sessionUi, "getAuthHeader").mockResolvedValue("Bearer test-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json({
          sections: {
            executive_summary: "Summary",
            threat_model: "Threats",
            methodology: "Method",
            evidence_and_results: "Evidence",
            mitigations: "Mitigations",
          },
          items: [
            { event_id: "evt-b", report_section: "not-a-section" },
            { event_id: "evt-a", report_section: "threat_model" },
            { event_id: "evt-a", report_section: "mitigations" },
          ],
        }),
      ),
    );

    const report = await getSessionReportDraft(SESSION_ID);

    expect(report).toMatchObject({
      sections: {
        executiveSummary: "Summary",
        threatModel: "Threats",
        methodology: "Method",
        evidenceAndResults: "Evidence",
        mitigations: "Mitigations",
      },
      selectedEvidenceIds: ["evt-a", "evt-b"],
      evidenceSectionsById: {
        "evt-a": "threat_model",
        "evt-b": "unassigned",
      },
    });
    expect(report.persistedSnapshot).toBe(
      createReportDraftSnapshot({
        sections: report.sections,
        selectedEvidenceIds: ["evt-b", "evt-a"],
        evidenceSectionsById: report.evidenceSectionsById,
      }),
    );
  });

  it("shares one cached request across report consumers", async () => {
    vi.spyOn(sessionUi, "getAuthHeader").mockResolvedValue("Bearer test-token");
    const fetchMock = vi.fn().mockResolvedValue(
      Response.json({
        sections: {},
        items: [],
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = createQueryClient();
    queryClient.setDefaultOptions({
      queries: { retry: false },
      mutations: { retry: false },
    });
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children);

    const first = renderHook(() => useSessionReportDraftQuery(SESSION_ID), {
      wrapper,
    });
    const second = renderHook(() => useSessionReportDraftQuery(SESSION_ID), {
      wrapper,
    });

    await waitFor(() => {
      expect(first.result.current.isSuccess).toBe(true);
      expect(second.result.current.isSuccess).toBe(true);
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("saves through a mutation and updates the persisted query cache", async () => {
    vi.spyOn(sessionUi, "getAuthHeader").mockResolvedValue("Bearer test-token");
    const responseBody = {
      sections: {
        executive_summary: "Saved summary",
        threat_model: "",
        methodology: "",
        evidence_and_results: "",
        mitigations: "",
      },
      items: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(Response.json(responseBody));
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = createQueryClient();
    const wrapper = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children);
    const mutation = renderHook(
      () => useSaveSessionReportDraftMutation(SESSION_ID),
      { wrapper },
    );
    const request = {
      sections: responseBody.sections,
      items: [],
    };

    await act(() => mutation.result.current.mutateAsync(request));

    const savedRequest = fetchMock.mock.calls[0]?.[0] as Request;
    expect(savedRequest.url).toContain(
      `/api/v1/sessions/${SESSION_ID}/report-draft`,
    );
    expect(savedRequest.method).toBe("PUT");
    expect(await savedRequest.json()).toEqual(request);
    expect(
      queryClient.getQueryData(sessionReportDraftQueryKey(SESSION_ID)),
    ).toMatchObject({
      sections: { executiveSummary: "Saved summary" },
      selectedEvidenceIds: [],
    });
  });
});
