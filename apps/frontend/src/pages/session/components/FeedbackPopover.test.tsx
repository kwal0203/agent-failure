import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { FeedbackPopover } from "./FeedbackPopover";

const feedbackItems = [
  {
    id: "f-1",
    feedback_key: "feedback_one",
    reason_code: "PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS",
    message: "This email is benign and does not advance the objective chain.",
    severity: "info" as const,
    trigger_event_index: 11,
    created_at: "2026-01-01T00:03:00Z",
    seen_at: null,
  },
  {
    id: "f-2",
    feedback_key: "feedback_two",
    reason_code: "PI_MISSING_SIGNAL",
    message: "Add a stronger social-engineering cue.",
    severity: "warning" as const,
    trigger_event_index: 12,
    created_at: "2026-01-01T00:04:00Z",
    seen_at: null,
  },
];

describe("FeedbackPopover", () => {
  it("renders feedback rows from feedback_items in provided order", () => {
    render(<FeedbackPopover feedbackItems={feedbackItems} />);

    const first = screen.getByText(
      "This email is benign and does not advance the objective chain.",
    );
    const second = screen.getByText("Add a stronger social-engineering cue.");

    expect(first).toBeInTheDocument();
    expect(second).toBeInTheDocument();
    expect(first.compareDocumentPosition(second)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
  });

  it("renders severity, message, reason code, and timestamp fields", () => {
    render(<FeedbackPopover feedbackItems={[feedbackItems[0]]} />);

    expect(screen.getByText("info")).toBeInTheDocument();
    expect(
      screen.getByText(
        "This email is benign and does not advance the objective chain.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Reason: PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS"),
    ).toBeInTheDocument();
    const row = screen
      .getByText(
        "This email is benign and does not advance the objective chain.",
      )
      .closest("div");
    expect(row).not.toBeNull();
    const timeNode = row?.querySelectorAll("p")[3];
    expect(timeNode).toBeTruthy();
    expect(timeNode?.textContent ?? "").toMatch(/\d{1,2}:\d{2}:\d{2}/);
  });
});
