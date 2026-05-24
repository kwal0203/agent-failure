import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { TimelineEvent } from "../types";
import { FeedbackColumn } from "./FeedbackColumn";

function makeTimelineEvent(
  overrides: Partial<TimelineEvent> = {},
): TimelineEvent {
  return {
    id: "trace-e1",
    timestamp: "2026-05-24T00:00:00.000Z",
    type: "important",
    granularity: "high",
    title: "Token disclosed",
    description: "Sensitive token was exposed during the session.",
    ...overrides,
  };
}

describe("FeedbackColumn", () => {
  it("renders read-only timeline events", () => {
    render(
      <FeedbackColumn
        feedbackLoading={false}
        feedbackReady={true}
        feedbackError={null}
        timelineEvents={[makeTimelineEvent()]}
      />,
    );

    expect(screen.getByText("Event Timeline")).toBeInTheDocument();
    expect(screen.getByText("Token disclosed")).toBeInTheDocument();
  });

  it("shows empty message when no timeline events", () => {
    render(
      <FeedbackColumn
        feedbackLoading={false}
        feedbackReady={true}
        feedbackError={null}
        timelineEvents={[]}
      />,
    );

    expect(screen.getByText("No events to display.")).toBeInTheDocument();
  });
});
