import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter } from "react-router";
import { RouterProvider } from "react-router/dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { sessionReportDraftQueryKey } from "../query/sessionReportDraft";
import { renderWithQueryClient } from "../test/renderWithQueryClient";
import SessionReportPage from "./SessionReportPage";
import * as sessionUi from "./session/ui";

const pdfMocks = vi.hoisted(() => ({
  renderSessionReportPdf: vi.fn(),
}));
vi.mock("./report/renderSessionReportPdf", () => pdfMocks);

const SESSION_ID = "11111111-1111-1111-1111-111111111111";

function mockJsonResponse(body: unknown, status = 200) {
  return Promise.resolve(Response.json(body, { status }));
}

function getRequestUrl(input: RequestInfo | URL): string {
  return input instanceof Request ? input.url : String(input);
}

function getRequestMethod(
  input: RequestInfo | URL,
  init?: RequestInit,
): string | undefined {
  return input instanceof Request ? input.method : init?.method;
}

async function getRequestJson(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Record<string, unknown>> {
  if (input instanceof Request) {
    return (await input.clone().json()) as Record<string, unknown>;
  }
  return JSON.parse(String(init?.body)) as Record<string, unknown>;
}

function renderReportPage(sessionId = SESSION_ID) {
  const router = createMemoryRouter(
    [
      {
        path: "/sessions/:sessionId/report",
        element: <SessionReportPage />,
      },
      {
        path: "/reports",
        element: <div>Reports destination</div>,
      },
    ],
    {
      initialEntries: [`/sessions/${sessionId}/report`],
    },
  );
  return renderWithQueryClient(<RouterProvider router={router} />);
}

describe("SessionReportPage evidence selection", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    pdfMocks.renderSessionReportPdf.mockRejectedValue(
      new Error("PDF test stopped after rendering"),
    );
    vi.spyOn(sessionUi, "getAuthHeader").mockResolvedValue("Bearer test-token");
    window.localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("persists selected evidence only after explicit save", async () => {
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = getRequestUrl(input);

        if (url.endsWith(`/api/v1/sessions/${SESSION_ID}/trace`)) {
          return mockJsonResponse({
            events: [
              {
                id: "evt-a",
                occurred_at: "2026-05-24T00:00:00Z",
                family: "learner",
                event_type: "ATTACK_EMAIL_SENT",
                payload: {
                  email_from: "attacker@example.com",
                  subject: "Hello",
                  malicious_marker: false,
                },
                report_selectable: true,
                evidence_type: "exploit_step",
                objective_keys: ["lab1.attack_delivery"],
                why_it_matters: "Delivery happened",
                default_priority: "medium",
              },
              {
                id: "evt-b",
                occurred_at: "2026-05-24T00:01:00Z",
                family: "agent",
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
          });
        }

        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "GET"
        ) {
          return mockJsonResponse({
            sections: {
              executive_summary: "",
              threat_model: "",
              methodology: "",
              evidence_and_results: "",
              mitigations: "",
            },
            items: [],
          });
        }

        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "PUT"
        ) {
          return mockJsonResponse({ items: [] });
        }

        throw new Error(`Unexpected URL: ${url}`);
      },
    );

    vi.stubGlobal("fetch", fetchMock);

    renderReportPage(SESSION_ID);

    const maliciousEmailChip = await screen.findByRole("button", {
      name: /benign email received/i,
    });
    fireEvent.click(maliciousEmailChip);
    const sectionSelectors = await screen.findAllByRole("combobox");
    fireEvent.change(sectionSelectors[0], {
      target: { value: "mitigations" },
    });
    const putCallsBeforeSave = fetchMock.mock.calls.filter(
      ([requestUrl, requestInit]) =>
        getRequestUrl(requestUrl).endsWith(
          `/api/v1/sessions/${SESSION_ID}/report-draft`,
        ) && getRequestMethod(requestUrl, requestInit) === "PUT",
    );
    expect(putCallsBeforeSave).toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(
      () => {
        const putCalls = fetchMock.mock.calls.filter(
          ([requestUrl, requestInit]) =>
            getRequestUrl(requestUrl).endsWith(
              `/api/v1/sessions/${SESSION_ID}/report-draft`,
            ) && getRequestMethod(requestUrl, requestInit) === "PUT",
        );
        expect(putCalls.length).toBeGreaterThan(0);
      },
      { timeout: 2500 },
    );
    const putCalls = fetchMock.mock.calls.filter(
      ([requestUrl, requestInit]) =>
        getRequestUrl(requestUrl).endsWith(
          `/api/v1/sessions/${SESSION_ID}/report-draft`,
        ) && getRequestMethod(requestUrl, requestInit) === "PUT",
    );
    const latestPut = putCalls[putCalls.length - 1];
    if (!latestPut) {
      throw new Error("Expected a report draft PUT request");
    }
    const body = await getRequestJson(latestPut[0], latestPut[1]);
    const items = body.items;
    expect(Array.isArray(items)).toBe(true);
    if (!Array.isArray(items)) {
      throw new Error("Expected report draft items to be an array");
    }
    expect(items).toHaveLength(1);
    expect(items[0]).toMatchObject({
      event_id: "evt-a",
      report_section: "mitigations",
    });
  });

  it("rehydrates selected state and section assignment from persisted evidence on page load", async () => {
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = getRequestUrl(input);

        if (url.endsWith(`/api/v1/sessions/${SESSION_ID}/trace`)) {
          return mockJsonResponse({
            events: [
              {
                id: "evt-a",
                occurred_at: "2026-05-24T00:00:00Z",
                family: "learner",
                event_type: "ATTACK_EMAIL_SENT",
                payload: {
                  email_from: "attacker@example.com",
                  subject: "Hello",
                  malicious_marker: true,
                },
                report_selectable: true,
                evidence_type: "exploit_step",
                objective_keys: ["lab1.attack_delivery"],
                why_it_matters: "Delivery happened",
                default_priority: "medium",
              },
            ],
            next_cursor: null,
          });
        }

        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "GET"
        ) {
          return mockJsonResponse({
            sections: {
              executive_summary: "Loaded summary",
              threat_model: "Loaded threat model",
              methodology: "Loaded methodology",
              evidence_and_results: "Loaded evidence",
              mitigations: "Loaded mitigations",
            },
            items: [
              {
                event_id: "evt-a",
                position: 0,
                title: "Malicious email received",
                description: "Email accepted.",
                details: null,
                occurred_at: "2026-05-24T00:00:00Z",
                trace_version: 1,
                event_index: 0,
                evidence_type: "exploit_step",
                objective_keys: ["lab1.attack_delivery"],
                why_it_matters: "Delivery happened",
                default_priority: "medium",
                citation_label: null,
                objective_mapping: null,
                evidence_strength: null,
                student_note: null,
                report_section: "threat_model",
                section_position: 0,
              },
            ],
          });
        }

        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "PUT"
        ) {
          return mockJsonResponse({ items: [] });
        }

        throw new Error(`Unexpected URL: ${url}`);
      },
    );

    vi.stubGlobal("fetch", fetchMock);

    renderReportPage(SESSION_ID);

    const selectedChip = await screen.findByRole("button", {
      name: /^malicious email received$/i,
    });

    await waitFor(() => {
      expect(selectedChip).toHaveAttribute("aria-pressed", "true");
    });
    expect(screen.getByDisplayValue("Threat Model")).toBeInTheDocument();
  });

  it("does not overwrite an edited draft when the persisted query refetches", async () => {
    let reportRequestCount = 0;
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = getRequestUrl(input);

        if (url.endsWith(`/api/v1/sessions/${SESSION_ID}/trace`)) {
          return mockJsonResponse({ events: [], next_cursor: null });
        }

        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "GET"
        ) {
          reportRequestCount += 1;
          return mockJsonResponse({
            sections: {
              executive_summary:
                reportRequestCount === 1
                  ? "Initial server summary"
                  : "Refetched server summary",
              threat_model: "",
              methodology: "",
              evidence_and_results: "",
              mitigations: "",
            },
            items: [],
          });
        }

        throw new Error(`Unexpected URL: ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    const { queryClient } = renderReportPage(SESSION_ID);
    const summary = await screen.findByLabelText("Executive Summary");
    await waitFor(() => expect(summary).toHaveValue("Initial server summary"));

    fireEvent.change(summary, {
      target: { value: "My unsaved local edit" },
    });
    await queryClient.invalidateQueries({
      queryKey: sessionReportDraftQueryKey(SESSION_ID),
      exact: true,
    });

    await waitFor(() => expect(reportRequestCount).toBe(2));
    expect(summary).toHaveValue("My unsaved local edit");
  });

  it("serializes saves and preserves edits made while a save is in flight", async () => {
    let resolveFirstSave: (() => void) | undefined;
    const putBodies: Array<Record<string, unknown>> = [];
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = getRequestUrl(input);

        if (url.endsWith(`/api/v1/sessions/${SESSION_ID}/trace`)) {
          return mockJsonResponse({ events: [], next_cursor: null });
        }

        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "GET"
        ) {
          return mockJsonResponse({
            sections: {
              executive_summary: "Initial summary",
              threat_model: "",
              methodology: "",
              evidence_and_results: "",
              mitigations: "",
            },
            items: [],
          });
        }

        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "PUT"
        ) {
          const body = await getRequestJson(input, init);
          putBodies.push(body);
          if (putBodies.length === 1) {
            return new Promise((resolve) => {
              resolveFirstSave = () => {
                resolve(Response.json(body));
              };
            });
          }
          return mockJsonResponse(body);
        }

        throw new Error(`Unexpected URL: ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    renderReportPage(SESSION_ID);
    const summary = await screen.findByLabelText("Executive Summary");
    await waitFor(() => expect(summary).toHaveValue("Initial summary"));

    fireEvent.change(summary, { target: { value: "First edit" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));
    await waitFor(() => expect(putBodies).toHaveLength(1));
    expect(screen.getByRole("status")).toHaveTextContent("Saving...");

    fireEvent.change(summary, { target: { value: "Second edit" } });
    expect(putBodies).toHaveLength(1);
    resolveFirstSave?.();

    await waitFor(() => expect(putBodies).toHaveLength(2), { timeout: 3_000 });
    expect(putBodies[0]).toMatchObject({
      sections: { executive_summary: "First edit" },
    });
    expect(putBodies[1]).toMatchObject({
      sections: { executive_summary: "Second edit" },
    });
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Saved"),
    );
    expect(summary).toHaveValue("Second edit");
  });

  it("debounces autosave until editing has paused", async () => {
    const putBodies: Array<Record<string, unknown>> = [];
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = getRequestUrl(input);

        if (url.endsWith(`/api/v1/sessions/${SESSION_ID}/trace`)) {
          return mockJsonResponse({ events: [], next_cursor: null });
        }
        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "GET"
        ) {
          return mockJsonResponse({
            sections: {
              executive_summary: "",
              threat_model: "",
              methodology: "",
              evidence_and_results: "",
              mitigations: "",
            },
            items: [],
          });
        }
        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "PUT"
        ) {
          const body = await getRequestJson(input, init);
          putBodies.push(body);
          return mockJsonResponse(body);
        }
        throw new Error(`Unexpected URL: ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    renderReportPage(SESSION_ID);
    const summary = await screen.findByLabelText("Executive Summary");
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Saved"),
    );
    vi.useFakeTimers();

    fireEvent.change(summary, { target: { value: "First keystroke" } });
    await act(() => vi.advanceTimersByTimeAsync(1_000));
    fireEvent.change(summary, { target: { value: "Finished edit" } });
    await act(() => vi.advanceTimersByTimeAsync(1_499));
    expect(putBodies).toHaveLength(0);

    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(putBodies).toHaveLength(1);
    expect(putBodies[0]).toMatchObject({
      sections: { executive_summary: "Finished edit" },
    });
  });

  it("flushes unsaved changes before internal navigation", async () => {
    const putBodies: Array<Record<string, unknown>> = [];
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = getRequestUrl(input);

        if (url.endsWith(`/api/v1/sessions/${SESSION_ID}/trace`)) {
          return mockJsonResponse({ events: [], next_cursor: null });
        }
        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "GET"
        ) {
          return mockJsonResponse({
            sections: {
              executive_summary: "",
              threat_model: "",
              methodology: "",
              evidence_and_results: "",
              mitigations: "",
            },
            items: [],
          });
        }
        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "PUT"
        ) {
          const body = await getRequestJson(input, init);
          putBodies.push(body);
          return mockJsonResponse(body);
        }
        throw new Error(`Unexpected URL: ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderReportPage(SESSION_ID);
    const summary = await screen.findByLabelText("Executive Summary");
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Saved"),
    );
    fireEvent.change(summary, { target: { value: "Save before leaving" } });
    fireEvent.click(screen.getByRole("button", { name: /back to reports/i }));

    expect(await screen.findByText("Reports destination")).toBeInTheDocument();
    expect(putBodies).toHaveLength(1);
    expect(putBodies[0]).toMatchObject({
      sections: { executive_summary: "Save before leaving" },
    });
  });

  it("flushes the latest draft before rendering a PDF", async () => {
    const operationOrder: string[] = [];
    let putBody: Record<string, unknown> | undefined;
    pdfMocks.renderSessionReportPdf.mockImplementation(async () => {
      operationOrder.push("render");
      throw new Error("PDF test stopped after rendering");
    });
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = getRequestUrl(input);

        if (url.endsWith(`/api/v1/sessions/${SESSION_ID}/trace`)) {
          return mockJsonResponse({ events: [], next_cursor: null });
        }
        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "GET"
        ) {
          return mockJsonResponse({
            sections: {
              executive_summary: "",
              threat_model: "",
              methodology: "",
              evidence_and_results: "",
              mitigations: "",
            },
            items: [],
          });
        }
        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "PUT"
        ) {
          operationOrder.push("save");
          putBody = await getRequestJson(input, init);
          return mockJsonResponse(putBody);
        }
        throw new Error(`Unexpected URL: ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    renderReportPage(SESSION_ID);
    const summary = await screen.findByLabelText("Executive Summary");
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Saved"),
    );
    fireEvent.change(summary, { target: { value: "Export this revision" } });
    fireEvent.click(screen.getByRole("button", { name: /^export$/i }));

    await waitFor(() =>
      expect(pdfMocks.renderSessionReportPdf).toHaveBeenCalledOnce(),
    );
    expect(operationOrder).toEqual(["save", "render"]);
    expect(putBody).toMatchObject({
      sections: { executive_summary: "Export this revision" },
    });
    expect(pdfMocks.renderSessionReportPdf).toHaveBeenCalledWith(
      expect.objectContaining({
        sections: expect.arrayContaining([
          {
            heading: "Executive Summary",
            content: "Export this revision",
          },
        ]),
      }),
    );
  });

  it("shows a failed save without repeatedly retrying the same snapshot", async () => {
    let putCount = 0;
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = getRequestUrl(input);

        if (url.endsWith(`/api/v1/sessions/${SESSION_ID}/trace`)) {
          return mockJsonResponse({ events: [], next_cursor: null });
        }
        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "GET"
        ) {
          return mockJsonResponse({
            sections: {
              executive_summary: "",
              threat_model: "",
              methodology: "",
              evidence_and_results: "",
              mitigations: "",
            },
            items: [],
          });
        }
        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "PUT"
        ) {
          putCount += 1;
          return mockJsonResponse({ error: { message: "Unavailable" } }, 503);
        }
        throw new Error(`Unexpected URL: ${url}`);
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    renderReportPage(SESSION_ID);
    const summary = await screen.findByLabelText("Executive Summary");
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Saved"),
    );
    fireEvent.change(summary, { target: { value: "Unsaved edit" } });
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent("Save failed"),
    );
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    vi.useFakeTimers();
    await act(() => vi.advanceTimersByTimeAsync(1_700));
    expect(putCount).toBe(1);
  });

  it("renders grouped evidence by assigned section", async () => {
    const fetchMock = vi.fn(
      async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = getRequestUrl(input);

        if (url.endsWith(`/api/v1/sessions/${SESSION_ID}/trace`)) {
          return mockJsonResponse({
            events: [
              {
                id: "evt-a",
                occurred_at: "2026-05-24T00:00:00Z",
                family: "learner",
                event_type: "ATTACK_EMAIL_SENT",
                payload: {
                  email_from: "attacker@example.com",
                  subject: "Hello",
                  malicious_marker: true,
                },
                report_selectable: true,
                evidence_type: "exploit_step",
                objective_keys: ["lab1.attack_delivery"],
                why_it_matters: "Delivery happened",
                default_priority: "medium",
              },
              {
                id: "evt-b",
                occurred_at: "2026-05-24T00:01:00Z",
                family: "learner",
                event_type: "TOKEN_DISCLOSED",
                payload: {},
                report_selectable: true,
                evidence_type: "exploit_outcome",
                objective_keys: ["lab1.token_disclosed"],
                why_it_matters: "Disclosure happened",
                default_priority: "high",
              },
            ],
            next_cursor: null,
          });
        }

        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "GET"
        ) {
          return mockJsonResponse({
            sections: {
              executive_summary: "",
              threat_model: "",
              methodology: "",
              evidence_and_results: "",
              mitigations: "",
            },
            items: [],
          });
        }

        if (
          url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-draft`) &&
          getRequestMethod(input, init) === "PUT"
        ) {
          return mockJsonResponse({ items: [] });
        }

        throw new Error(`Unexpected URL: ${url}`);
      },
    );

    vi.stubGlobal("fetch", fetchMock);
    renderReportPage(SESSION_ID);

    const firstChip = await screen.findByRole("button", {
      name: /malicious email received/i,
    });
    fireEvent.click(firstChip);

    const secondChip = await screen.findByRole("button", {
      name: /token disclosed/i,
    });
    fireEvent.click(secondChip);

    const selectors = await screen.findAllByRole("combobox");
    fireEvent.change(selectors[0], { target: { value: "methodology" } });
    fireEvent.change(selectors[1], { target: { value: "mitigations" } });

    await waitFor(() => {
      const methodologyHeader = screen.getByText("Methodology", {
        selector: "p",
      });
      const methodologyCard = methodologyHeader.closest("div");
      expect(methodologyCard?.textContent).toContain("Token disclosed");

      const mitigationsHeader = screen.getByText("Mitigations", {
        selector: "p",
      });
      const mitigationsCard = mitigationsHeader.closest("div");
      expect(mitigationsCard?.textContent).toContain(
        "Malicious email received",
      );
    });
  });
});
