import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { TimelineEvent } from "../types";
import { FeedbackColumn } from "./FeedbackColumn";

vi.mock("../ui", () => ({
  API_BASE: "http://localhost:8000",
  getAuthHeader: () => "Bearer test-token",
  DEMO_H2_STYLE: {},
}));

function makeTimelineEvent(
  overrides: Partial<TimelineEvent> = {},
): TimelineEvent {
  return {
    id: "trace-11111111-1111-1111-1111-111111111111",
    timestamp: "2026-05-17T10:00:00.000Z",
    type: "important",
    granularity: "high",
    title: "Token disclosed",
    description: "Sensitive token exposed.",
    report_selectable: true,
    evidence_type: "exploit_outcome",
    objective_keys: ["lab1.token_disclosed"],
    why_it_matters: "Direct exploit proof",
    default_priority: "high",
    ...overrides,
  };
}

describe("FeedbackColumn", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn(async (input, init) => {
      const url = String(input);
      if (url.includes("/report-evidence") && init?.method === "GET") {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                event_id: "11111111-1111-1111-1111-111111111111",
                position: 0,
                title: "Token disclosed",
                description: "Sensitive token exposed.",
                details: null,
                occurred_at: "2026-05-17T10:00:00.000Z",
                trace_version: 1,
                event_index: 1,
                evidence_type: "exploit_outcome",
                objective_keys: ["lab1.token_disclosed"],
                why_it_matters: "Direct exploit proof",
                default_priority: "high",
                citation_label: "E1",
                objective_mapping: [],
                evidence_strength: "high",
                student_note: null,
              },
            ],
          }),
        } as Response;
      }
      if (url.includes("/report-evidence") && init?.method === "PUT") {
        return {
          ok: true,
          json: async () => ({ items: [] }),
        } as Response;
      }
      throw new Error(`Unhandled fetch: ${url}`);
    }) as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders selected count and toggles selection on chip click", async () => {
    render(
      <FeedbackColumn
        sessionId="s1"
        feedbackLoading={false}
        feedbackReady
        feedbackError={null}
        timelineEvents={[makeTimelineEvent()]}
      />,
    );

    await waitFor(() =>
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/sessions/s1/report-evidence",
        expect.objectContaining({ method: "GET" }),
      ),
    );

    const chip = screen.getByRole("button", { name: /token disclosed/i });
    await waitFor(() => {
      expect(screen.getByText(/Selected:\s*1/)).toBeInTheDocument();
    });

    fireEvent.click(chip);
    await waitFor(() => {
      expect(screen.getByText(/Selected:\s*0/)).toBeInTheDocument();
    });

    fireEvent.click(chip);
    await waitFor(() => {
      expect(screen.getByText(/Selected:\s*1/)).toBeInTheDocument();
    });
  });

  it("hydrates preselected trace events from persisted report evidence", async () => {
    globalThis.fetch = vi.fn(async (input, init) => {
      const url = String(input);
      if (url.includes("/report-evidence") && init?.method === "GET") {
        return {
          ok: true,
          json: async () => ({
            items: [
              {
                event_id: "11111111-1111-1111-1111-111111111111",
                position: 0,
                title: "Token disclosed",
                description: "Sensitive token exposed.",
                details: null,
                occurred_at: "2026-05-17T10:00:00.000Z",
                trace_version: 1,
                event_index: 1,
                evidence_type: "exploit_outcome",
                objective_keys: ["lab1.token_disclosed"],
                why_it_matters: "Direct exploit proof",
                default_priority: "high",
                citation_label: "E1",
                objective_mapping: [],
                evidence_strength: "high",
                student_note: null,
              },
            ],
          }),
        } as Response;
      }
      if (url.includes("/report-evidence") && init?.method === "PUT") {
        return {
          ok: true,
          json: async () => ({ items: [] }),
        } as Response;
      }
      throw new Error(`Unhandled fetch: ${url}`);
    }) as typeof fetch;

    render(
      <FeedbackColumn
        sessionId="s1"
        feedbackLoading={false}
        feedbackReady
        feedbackError={null}
        timelineEvents={[makeTimelineEvent()]}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("Selected: 1")).toBeInTheDocument();
    });
  });

  it("sends full selected set through debounced PUT", async () => {
    globalThis.fetch = vi.fn(async (input, init) => {
      const url = String(input);
      if (url.includes("/report-evidence") && init?.method === "GET") {
        return {
          ok: true,
          json: async () => ({ items: [] }),
        } as Response;
      }
      if (url.includes("/report-evidence") && init?.method === "PUT") {
        return {
          ok: true,
          json: async () => ({ items: [] }),
        } as Response;
      }
      throw new Error(`Unhandled fetch: ${url}`);
    }) as typeof fetch;

    render(
      <FeedbackColumn
        sessionId="s1"
        feedbackLoading={false}
        feedbackReady
        feedbackError={null}
        timelineEvents={[makeTimelineEvent()]}
      />,
    );

    const chip = await screen.findByRole("button", {
      name: /token disclosed/i,
    });
    await waitFor(() => {
      expect(screen.getByText(/Selected:\s*0/)).toBeInTheDocument();
    });
    fireEvent.click(chip);

    await waitFor(() =>
      expect(globalThis.fetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/sessions/s1/report-evidence",
        expect.objectContaining({
          method: "PUT",
        }),
      ),
    );

    const putCall = (
      globalThis.fetch as unknown as ReturnType<typeof vi.fn>
    ).mock.calls.find(
      ([url, init]) =>
        String(url).includes("/report-evidence") && init?.method === "PUT",
    );
    expect(putCall).toBeDefined();
    const body = JSON.parse(String(putCall?.[1]?.body));
    expect(body.items).toHaveLength(1);
    expect(body.items[0].event_id).toBe("11111111-1111-1111-1111-111111111111");
  });

  it("renders non-selectable events as non-button cards", async () => {
    render(
      <FeedbackColumn
        sessionId="s1"
        feedbackLoading={false}
        feedbackReady
        feedbackError={null}
        timelineEvents={[
          makeTimelineEvent({
            id: "trace-22222222-2222-2222-2222-222222222222",
            title: "Noise event",
            report_selectable: false,
          }),
        ]}
      />,
    );

    expect(screen.queryByRole("button", { name: /noise event/i })).toBeNull();
    expect(screen.getByText("Noise event")).toBeInTheDocument();
  });
});
