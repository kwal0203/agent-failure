import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SessionHeaderStatus } from "./SessionHeaderStatus";

function baseProps() {
  return {
    progressReady: true,
    progressChips: [],
    agentStatus: "idle" as const,
    completionStatus: "in_progress" as const,
    completedAt: null,
    completionReasonCode: null,
    unreadFeedbackCount: 0,
    feedbackItems: [],
    feedbackPanelOpen: false,
    onFeedbackChipClick: vi.fn(),
    hasUnreadHint: false,
    unlockedHints: [],
    hintsReady: true,
    sessionState: "ACTIVE",
    hintsPanelOpen: false,
    onHintsChipClick: vi.fn(),
    canStopSession: true,
    stoppingSession: false,
    onStopSession: vi.fn(),
  };
}

describe("SessionHeaderStatus feedback chip", () => {
  it("shows unread feedback count badge when unread_feedback_count > 0", () => {
    const props = {
      ...baseProps(),
      unreadFeedbackCount: 3,
      feedbackItems: [
        {
          id: "fb-1",
          feedback_key: "lab1_benign_email_not_progressing",
          reason_code: "PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS",
          message: "Benign email sent.",
          severity: "info" as const,
          trigger_event_index: 10,
          created_at: "2026-04-24T20:30:00Z",
          seen_at: null,
        },
      ],
    };

    render(<SessionHeaderStatus {...props} />);

    const feedbackButton = screen.getByRole("button", { name: /feedback/i });
    expect(feedbackButton).toHaveTextContent("Feedback");
    expect(feedbackButton).toHaveTextContent("(1)");
  });

  it("hides unread feedback badge when unread_feedback_count is 0", () => {
    const props = {
      ...baseProps(),
      unreadFeedbackCount: 0,
    };

    render(<SessionHeaderStatus {...props} />);

    const feedbackButton = screen.getByRole("button", { name: /^feedback$/i });
    expect(feedbackButton).toBeInTheDocument();
    expect(feedbackButton).not.toHaveTextContent("(0)");
  });

  it("uses feedback chip click handler to open panel flow", () => {
    const onFeedbackChipClick = vi.fn();
    const props = {
      ...baseProps(),
      onFeedbackChipClick,
    };

    render(<SessionHeaderStatus {...props} />);

    fireEvent.click(screen.getByRole("button", { name: /^feedback$/i }));
    expect(onFeedbackChipClick).toHaveBeenCalledTimes(1);
  });
});
