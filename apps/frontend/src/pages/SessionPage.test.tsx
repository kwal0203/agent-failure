import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SessionPage from "./SessionPage";
import { useSessionStream } from "../hooks/useSessionStream";

vi.mock("../hooks/useSessionStream", () => ({
  useSessionStream: vi.fn(),
}));

function mockJsonResponse(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function renderSessionPage() {
  return render(
    <MemoryRouter initialEntries={["/sessions/11111111-1111-1111-1111-111111111111"]}>
      <Routes>
        <Route path="/sessions/:sessionId" element={<SessionPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("SessionPage learner feedback panel", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(useSessionStream).mockReturnValue({
      connectionState: "open",
      messages: [],
      sendPrompt: vi.fn(),
      reconnect: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders explicit empty state when evaluator feedback is empty", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/evaluator-feedback")) {
          return mockJsonResponse({ feedback: [] });
        }
        return mockJsonResponse({
          session: {
            id: "11111111-1111-1111-1111-111111111111",
            lab_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            lab_version_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            state: "ACTIVE",
            runtime_substate: "RUNNING",
            resume_mode: "fresh",
            interactive: true,
            created_at: "2026-01-01T00:00:00Z",
            started_at: null,
            ended_at: null,
          },
        });
      }),
    );

    renderSessionPage();

    expect(await screen.findByRole("heading", { name: "Learner feedback" })).toBeInTheDocument();
    expect(await screen.findByText("No learner feedback yet.")).toBeInTheDocument();
  });

  it("renders learner feedback entries from evaluator feedback response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/evaluator-feedback")) {
          return mockJsonResponse({
            feedback: [
              {
                status: "learned",
                reason_code: "PI_SECRET_EXFILTRATION_DETECTED",
                evidence_snippet: "FLAG{abc123}",
              },
              {
                status: "progress",
                reason_code: "PI_ATTACK_ATTEMPT_BLOCKED",
                evidence_snippet:
                  "Attack attempt blocked by model_policy (POLICY_DENIED)",
              },
            ],
          });
        }
        return mockJsonResponse({
          session: {
            id: "11111111-1111-1111-1111-111111111111",
            lab_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            lab_version_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            state: "ACTIVE",
            runtime_substate: "RUNNING",
            resume_mode: "fresh",
            interactive: true,
            created_at: "2026-01-01T00:00:00Z",
            started_at: null,
            ended_at: null,
          },
        });
      }),
    );

    renderSessionPage();

    expect((await screen.findAllByText("learned")).length).toBeGreaterThan(0);
    expect(await screen.findByText("FLAG{abc123}")).toBeInTheDocument();
    expect((await screen.findAllByText("progress")).length).toBeGreaterThan(0);
    expect(
      await screen.findByText("Attack attempt blocked by model_policy (POLICY_DENIED)"),
    ).toBeInTheDocument();
  });
});
