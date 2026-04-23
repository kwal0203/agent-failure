import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SessionCompletionIndicator } from "./SessionCompletionIndicator";

describe("SessionCompletionIndicator", () => {
  it("renders in-progress status", () => {
    render(
      <SessionCompletionIndicator
        completionStatus="in_progress"
        completedAt={null}
        completionReasonCode={null}
      />,
    );

    expect(screen.getByText("Outcome: in_progress")).toBeInTheDocument();
  });

  it("renders completed-success status with details", () => {
    render(
      <SessionCompletionIndicator
        completionStatus="completed_success"
        completedAt="2026-01-01T00:05:00Z"
        completionReasonCode="ALL_REQUIRED_OBJECTIVES_COMPLETED"
      />,
    );

    expect(screen.getByText("Outcome: completed_success")).toBeInTheDocument();
    expect(
      screen.getByText(/Reason ALL_REQUIRED_OBJECTIVES_COMPLETED/),
    ).toBeInTheDocument();
  });

  it("renders completed-failure status", () => {
    render(
      <SessionCompletionIndicator
        completionStatus="completed_failure"
        completedAt="2026-01-01T00:06:00Z"
        completionReasonCode="FAILED_POLICY_CHECK"
      />,
    );

    expect(screen.getByText("Outcome: completed_failure")).toBeInTheDocument();
  });

  it("renders failure placeholder when no completion details are available", () => {
    render(
      <SessionCompletionIndicator
        completionStatus="completed_failure"
        completedAt={null}
        completionReasonCode={null}
      />,
    );

    expect(
      screen.getByText("Failure handling UX placeholder."),
    ).toBeInTheDocument();
  });
});
