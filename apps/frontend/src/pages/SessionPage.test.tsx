import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useSessionStream } from "../hooks/useSessionStream";
import SessionPage from "./SessionPage";

vi.mock("../hooks/useSessionStream", () => ({
  useSessionStream: vi.fn(),
}));

const SESSION_A = "11111111-1111-1111-1111-111111111111";
const SESSION_B = "22222222-2222-2222-2222-222222222222";

function mockJsonResponse(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

function feedbackItem(params: {
  id: string;
  key: string;
  reason: string;
  message: string;
  severity?: "info" | "warning" | "error";
  createdAt?: string;
  seenAt?: string | null;
}) {
  return {
    id: params.id,
    feedback_key: params.key,
    reason_code: params.reason,
    message: params.message,
    severity: params.severity ?? "info",
    trigger_event_index: 12,
    created_at: params.createdAt ?? "2026-01-01T00:03:00Z",
    seen_at: params.seenAt ?? null,
  };
}

function sessionMetadata(params: {
  id: string;
  labId: string;
  feedbackItems?: ReturnType<typeof feedbackItem>[];
  unreadFeedbackCount?: number;
}) {
  const feedbackItems = params.feedbackItems ?? [];
  return {
    session: {
      id: params.id,
      lab_id: params.labId,
      lab_version_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      state: "IDLE",
      runtime_substate: null,
      resume_mode: "fresh",
      interactive: true,
      created_at: "2026-01-01T00:00:00Z",
      started_at: null,
      ended_at: null,
      completion_status: "in_progress",
      completed_at: null,
      completion_reason_code: null,
      progress_chips: [],
      hints: [],
      unread_hint_count: 0,
      feedback_items: feedbackItems,
      feedback: feedbackItems,
      unread_feedback_count: params.unreadFeedbackCount ?? 0,
    },
  };
}

function renderSessionPage(sessionId = SESSION_A) {
  return render(
    <MemoryRouter initialEntries={[`/sessions/${sessionId}`]}>
      <Routes>
        <Route path="/sessions/:sessionId" element={<SessionPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("SessionPage metadata-driven feedback", () => {
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

  it("marks feedback as seen through backend and refreshes metadata on panel open", async () => {
    let seen = false;
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);

      if (url.endsWith(`/api/v1/sessions/${SESSION_A}/trace`)) {
        return mockJsonResponse({ events: [], next_cursor: null });
      }

      if (url.endsWith(`/api/v1/sessions/${SESSION_A}/feedback/mark-seen`)) {
        expect(init?.method).toBe("POST");
        seen = true;
        return mockJsonResponse({ session_id: SESSION_A, updated_count: 1 });
      }

      if (url.endsWith(`/api/v1/sessions/${SESSION_A}`)) {
        const items = [
          feedbackItem({
            id: "fb-1",
            key: "lab1_benign_email_not_progressing",
            reason: "PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS",
            message: "This email is benign and does not progress the lab.",
            seenAt: seen ? "2026-01-01T00:04:00Z" : null,
          }),
        ];
        return mockJsonResponse(
          sessionMetadata({
            id: SESSION_A,
            labId: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            feedbackItems: items,
            unreadFeedbackCount: seen ? 0 : 1,
          }),
        );
      }

      throw new Error(`Unexpected URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    renderSessionPage(SESSION_A);

    const feedbackButton = await screen.findByRole("button", {
      name: /feedback/i,
    });
    expect(feedbackButton).toHaveTextContent("(1)");

    fireEvent.click(feedbackButton);

    expect(
      await screen.findByText(
        "This email is benign and does not progress the lab.",
      ),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(
        fetchMock.mock.calls.some(([requestUrl, requestInit]) => {
          return (
            String(requestUrl).endsWith(
              `/api/v1/sessions/${SESSION_A}/feedback/mark-seen`,
            ) && requestInit?.method === "POST"
          );
        }),
      ).toBe(true);
    });

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /^feedback$/i }),
      ).toBeInTheDocument();
    });
  });

  it("keeps feedback state stable across refresh/reconnect", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith(`/api/v1/sessions/${SESSION_A}/trace`)) {
          return mockJsonResponse({ events: [], next_cursor: null });
        }
        if (url.endsWith(`/api/v1/sessions/${SESSION_A}`)) {
          return mockJsonResponse(
            sessionMetadata({
              id: SESSION_A,
              labId: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
              feedbackItems: [
                feedbackItem({
                  id: "fb-refresh",
                  key: "generic_feedback",
                  reason: "PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS",
                  message: "Feedback persists across reconnect.",
                }),
              ],
              unreadFeedbackCount: 1,
            }),
          );
        }
        throw new Error(`Unexpected URL: ${url}`);
      }),
    );

    const first = renderSessionPage(SESSION_A);
    expect(
      await screen.findByRole("button", { name: /feedback/i }),
    ).toHaveTextContent("(1)");
    first.unmount();

    renderSessionPage(SESSION_A);
    const feedbackButton = await screen.findByRole("button", {
      name: /feedback/i,
    });
    expect(feedbackButton).toHaveTextContent("(1)");

    fireEvent.click(feedbackButton);
    expect(
      await screen.findByText("Feedback persists across reconnect."),
    ).toBeInTheDocument();
  });

  it("renders feedback for the active session only when switching labs/sessions", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith(`/api/v1/sessions/${SESSION_A}/trace`)) {
          return mockJsonResponse({ events: [], next_cursor: null });
        }
        if (url.endsWith(`/api/v1/sessions/${SESSION_B}/trace`)) {
          return mockJsonResponse({ events: [], next_cursor: null });
        }
        if (url.endsWith(`/api/v1/sessions/${SESSION_A}`)) {
          return mockJsonResponse(
            sessionMetadata({
              id: SESSION_A,
              labId: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
              feedbackItems: [
                feedbackItem({
                  id: "fb-a",
                  key: "feedback_a",
                  reason: "PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS",
                  message: "Session A feedback",
                }),
              ],
              unreadFeedbackCount: 1,
            }),
          );
        }
        if (url.endsWith(`/api/v1/sessions/${SESSION_B}`)) {
          return mockJsonResponse(
            sessionMetadata({
              id: SESSION_B,
              labId: "33333333-3333-3333-3333-333333333333",
              feedbackItems: [
                feedbackItem({
                  id: "fb-b",
                  key: "feedback_b",
                  reason: "PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS",
                  message: "Session B feedback",
                }),
              ],
              unreadFeedbackCount: 1,
            }),
          );
        }
        throw new Error(`Unexpected URL: ${url}`);
      }),
    );

    const first = renderSessionPage(SESSION_A);
    fireEvent.click(await screen.findByRole("button", { name: /feedback/i }));
    expect(await screen.findByText("Session A feedback")).toBeInTheDocument();
    expect(screen.queryByText("Session B feedback")).not.toBeInTheDocument();

    first.unmount();
    renderSessionPage(SESSION_B);
    fireEvent.click(await screen.findByRole("button", { name: /feedback/i }));
    expect(await screen.findByText("Session B feedback")).toBeInTheDocument();
    expect(screen.queryByText("Session A feedback")).not.toBeInTheDocument();
  });

  it("renders feedback generically with no lab-specific branching", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith(`/api/v1/sessions/${SESSION_A}/trace`)) {
          return mockJsonResponse({ events: [], next_cursor: null });
        }
        if (url.endsWith(`/api/v1/sessions/${SESSION_B}/trace`)) {
          return mockJsonResponse({ events: [], next_cursor: null });
        }
        if (url.endsWith(`/api/v1/sessions/${SESSION_A}`)) {
          return mockJsonResponse(
            sessionMetadata({
              id: SESSION_A,
              labId: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
              feedbackItems: [
                feedbackItem({
                  id: "fb-generic-a",
                  key: "generic",
                  reason: "PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS",
                  message: "Same generic rendering",
                  severity: "warning",
                }),
              ],
              unreadFeedbackCount: 1,
            }),
          );
        }
        if (url.endsWith(`/api/v1/sessions/${SESSION_B}`)) {
          return mockJsonResponse(
            sessionMetadata({
              id: SESSION_B,
              labId: "33333333-3333-3333-3333-333333333333",
              feedbackItems: [
                feedbackItem({
                  id: "fb-generic-b",
                  key: "generic",
                  reason: "PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS",
                  message: "Same generic rendering",
                  severity: "warning",
                }),
              ],
              unreadFeedbackCount: 1,
            }),
          );
        }
        throw new Error(`Unexpected URL: ${url}`);
      }),
    );

    const first = renderSessionPage(SESSION_A);
    fireEvent.click(await screen.findByRole("button", { name: /feedback/i }));
    expect(
      await screen.findByText("Same generic rendering"),
    ).toBeInTheDocument();
    expect(screen.getByText("warning")).toBeInTheDocument();
    expect(
      screen.getByText("Reason: PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS"),
    ).toBeInTheDocument();

    first.unmount();
    renderSessionPage(SESSION_B);
    fireEvent.click(await screen.findByRole("button", { name: /feedback/i }));
    expect(
      await screen.findByText("Same generic rendering"),
    ).toBeInTheDocument();
    expect(screen.getByText("warning")).toBeInTheDocument();
    expect(
      screen.getByText("Reason: PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS"),
    ).toBeInTheDocument();
  });
});
