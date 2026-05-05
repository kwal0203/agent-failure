import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStream } from "../hooks/useSessionStream";
import SessionPage from "./SessionPage";
import * as sessionUi from "./session/ui";

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
    <MemoryRouter
      initialEntries={["/sessions/11111111-1111-1111-1111-111111111111"]}
    >
      <Routes>
        <Route path="/sessions/:sessionId" element={<SessionPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("SessionPage completion indicator", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(sessionUi, "getAuthHeader").mockReturnValue("Bearer test-token");
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

  it("renders completed_success from metadata", async () => {
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
            state: "COMPLETED",
            runtime_substate: null,
            resume_mode: "fresh",
            interactive: false,
            created_at: "2026-01-01T00:00:00Z",
            started_at: "2026-01-01T00:00:05Z",
            ended_at: "2026-01-01T00:05:00Z",
            completion_status: "completed_success",
            completed_at: "2026-01-01T00:05:00Z",
            completion_reason_code: "ALL_REQUIRED_OBJECTIVES_COMPLETED",
            progress_chips: [],
            hints: [],
            unread_hint_count: 0,
          },
        });
      }),
    );

    renderSessionPage();
    expect(
      await screen.findByRole("dialog", { name: "Session completion success" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Outcome: completed_success"),
    ).not.toBeInTheDocument();
  });

  it("locks compose and action buttons when completion_status is completed_success", async () => {
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
            state: "COMPLETED",
            runtime_substate: null,
            resume_mode: "fresh",
            interactive: false,
            created_at: "2026-01-01T00:00:00Z",
            started_at: "2026-01-01T00:00:05Z",
            ended_at: "2026-01-01T00:05:00Z",
            completion_status: "completed_success",
            completed_at: "2026-01-01T00:05:00Z",
            completion_reason_code: "ALL_REQUIRED_OBJECTIVES_COMPLETED",
            progress_chips: [],
            hints: [],
            unread_hint_count: 0,
          },
        });
      }),
    );

    renderSessionPage();
    expect(
      await screen.findByRole("dialog", { name: "Session completion success" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Email" })).toBeDisabled();
    expect(screen.getByPlaceholderText("Type your prompt...")).toBeDisabled();
    expect(screen.getByLabelText("Send prompt")).toBeDisabled();
  });

  it("closes success modal when the close button is clicked", async () => {
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
            state: "COMPLETED",
            runtime_substate: null,
            resume_mode: "fresh",
            interactive: false,
            created_at: "2026-01-01T00:00:00Z",
            started_at: "2026-01-01T00:00:05Z",
            ended_at: "2026-01-01T00:05:00Z",
            completion_status: "completed_success",
            completed_at: "2026-01-01T00:05:00Z",
            completion_reason_code: "ALL_REQUIRED_OBJECTIVES_COMPLETED",
            progress_chips: [],
            hints: [],
            unread_hint_count: 0,
          },
        });
      }),
    );

    renderSessionPage();
    expect(
      await screen.findByRole("dialog", { name: "Session completion success" }),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Close success popup" }),
    );
    expect(
      screen.queryByRole("dialog", { name: "Session completion success" }),
    ).not.toBeInTheDocument();
  });

  it("renders completed_failure from metadata", async () => {
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
            state: "FAILED",
            runtime_substate: null,
            resume_mode: "fresh",
            interactive: false,
            created_at: "2026-01-01T00:00:00Z",
            started_at: "2026-01-01T00:00:05Z",
            ended_at: "2026-01-01T00:06:00Z",
            completion_status: "completed_failure",
            completed_at: "2026-01-01T00:06:00Z",
            completion_reason_code: "FAILED_POLICY_CHECK",
            progress_chips: [],
            hints: [],
            unread_hint_count: 0,
          },
        });
      }),
    );

    renderSessionPage();
    expect(
      await screen.findByText("Outcome: completed_failure"),
    ).toBeInTheDocument();
  });

  it("does not render an outcome chip for in_progress", async () => {
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
            started_at: "2026-01-01T00:00:05Z",
            ended_at: null,
            completion_status: "in_progress",
            completed_at: null,
            completion_reason_code: null,
            progress_chips: [],
            hints: [],
            unread_hint_count: 0,
          },
        });
      }),
    );

    renderSessionPage();
    await screen.findByText("Session: active");
    expect(screen.queryByText("Outcome: in_progress")).not.toBeInTheDocument();
  });

  it("does not change completion indicator when objective chips change but completion_status remains in_progress", async () => {
    let progressed = false;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/evaluator-feedback")) {
          progressed = true;
          return mockJsonResponse({
            feedback: [
              {
                status: "progress",
                reason_code: "PI_GLOBAL_MALICIOUS_ARTIFACT_ENTERED_CONTEXT",
                evidence_snippet: "artifact entered context",
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
            completion_status: "in_progress",
            completed_at: null,
            completion_reason_code: null,
            progress_chips: [
              {
                objective_key: "malicious_instructions_entered_context",
                label: "Malicious instructions entered context",
                status: progressed ? "complete" : "pending",
                completed_at: progressed ? "2026-01-01T00:01:00Z" : null,
                updated_at: "2026-01-01T00:01:00Z",
              },
            ],
            hints: [],
            unread_hint_count: 0,
          },
        });
      }),
    );

    renderSessionPage();

    await screen.findByText("Malicious instructions entered context", {
      exact: false,
    });
    expect(screen.queryByText("Outcome: in_progress")).not.toBeInTheDocument();
    expect(
      screen.getByText("Malicious instructions entered context", {
        exact: false,
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Outcome: completed_success"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Outcome: completed_failure"),
    ).not.toBeInTheDocument();
  });

  it("does not render in_progress outcome chip even when all objective chips are complete", async () => {
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
            started_at: "2026-01-01T00:00:05Z",
            ended_at: null,
            completion_status: "in_progress",
            completed_at: null,
            completion_reason_code: null,
            progress_chips: [
              {
                objective_key: "malicious_email_injected",
                label: "Malicious email injected",
                status: "complete",
                completed_at: "2026-01-01T00:01:00Z",
                updated_at: "2026-01-01T00:01:00Z",
              },
              {
                objective_key: "malicious_instructions_entered_context",
                label: "Malicious instructions entered context",
                status: "complete",
                completed_at: "2026-01-01T00:02:00Z",
                updated_at: "2026-01-01T00:02:00Z",
              },
              {
                objective_key: "token_exposed",
                label: "Private information revealed",
                status: "complete",
                completed_at: "2026-01-01T00:03:00Z",
                updated_at: "2026-01-01T00:03:00Z",
              },
            ],
            hints: [],
            unread_hint_count: 0,
          },
        });
      }),
    );

    renderSessionPage();

    await screen.findByText("Private information revealed", { exact: false });
    expect(screen.queryByText("Outcome: in_progress")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Outcome: completed_success"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Outcome: completed_failure"),
    ).not.toBeInTheDocument();
  });
});
