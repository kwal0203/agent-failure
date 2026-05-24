import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SessionReportPage from "./SessionReportPage";
import * as sessionUi from "./session/ui";

const SESSION_ID = "11111111-1111-1111-1111-111111111111";

function mockJsonResponse(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function renderReportPage(sessionId = SESSION_ID) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${sessionId}/report`]}>
      <Routes>
        <Route
          path="/sessions/:sessionId/report"
          element={<SessionReportPage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("SessionReportPage evidence selection", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(sessionUi, "getAuthHeader").mockReturnValue("Bearer test-token");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("persists selected evidence with a debounced full PUT payload", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

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
        url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-evidence`) &&
        init?.method === "GET"
      ) {
        return mockJsonResponse({ items: [] });
      }

      if (
        url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-evidence`) &&
        init?.method === "PUT"
      ) {
        return mockJsonResponse({ items: [] });
      }

      throw new Error(`Unexpected URL: ${url}`);
    });

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

    await waitFor(
      () => {
        const putCalls = fetchMock.mock.calls.filter(
          ([requestUrl, requestInit]) =>
            String(requestUrl).endsWith(
              `/api/v1/sessions/${SESSION_ID}/report-evidence`,
            ) && requestInit?.method === "PUT",
        );
        expect(putCalls.length).toBeGreaterThan(0);

        const body = JSON.parse(
          String(putCalls[putCalls.length - 1]?.[1]?.body),
        );
        expect(Array.isArray(body.items)).toBe(true);
        expect(body.items).toHaveLength(1);
        expect(body.items[0].event_id).toBe("evt-a");
        expect(body.items[0].report_section).toBe("mitigations");
      },
      { timeout: 2500 },
    );
  });

  it("rehydrates selected state and section assignment from persisted evidence on page load", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

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
        url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-evidence`) &&
        init?.method === "GET"
      ) {
        return mockJsonResponse({
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
        url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-evidence`) &&
        init?.method === "PUT"
      ) {
        return mockJsonResponse({ items: [] });
      }

      throw new Error(`Unexpected URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    renderReportPage(SESSION_ID);

    const selectedChip = await screen.findByRole("button", {
      name: /malicious email received/i,
    });

    await waitFor(() => {
      expect(selectedChip).toHaveAttribute("aria-pressed", "true");
    });
    expect(screen.getByDisplayValue("Threat Model")).toBeInTheDocument();
  });

  it("renders grouped evidence by assigned section", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

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
        url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-evidence`) &&
        init?.method === "GET"
      ) {
        return mockJsonResponse({ items: [] });
      }

      if (
        url.endsWith(`/api/v1/sessions/${SESSION_ID}/report-evidence`) &&
        init?.method === "PUT"
      ) {
        return mockJsonResponse({ items: [] });
      }

      throw new Error(`Unexpected URL: ${url}`);
    });

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
