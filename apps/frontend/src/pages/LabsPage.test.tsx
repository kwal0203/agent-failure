import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LabCatalog, type LabCatalogItem } from "./LabsPage";

vi.mock("../auth/useAuth", () => ({
  useAuth: () => ({
    logout: vi.fn(),
  }),
}));

describe("LabCatalog", () => {
  it("renders populated catalog with metadata and launch action", async () => {
    const labs: LabCatalogItem[] = [
      {
        id: "11111111-1111-1111-1111-111111111111",
        slug: "prompt-injection-basics",
        name: "Prompt Injection Basics",
        summary: "Practice attacking a retrieval-enabled agent.",
        capabilities: {
          supports_resume: true,
          supports_uploads: false,
        },
      },
    ];

    const loadLabs = vi.fn(async () => labs);
    const onOpenPreLab = vi.fn();

    render(
      <LabCatalog
        apiBaseUrl="http://localhost:8000"
        learnerLabel="Demo Learner"
        mode="debug"
        loadLabs={loadLabs}
        onOpenPreLab={onOpenPreLab}
      />,
    );

    expect(
      await screen.findByRole("heading", {
        name: /Prompt Injection Basics/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/slug:/i)).toBeInTheDocument();
    expect(screen.getByText(/resume: yes \| uploads: no/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Launch lab" }));

    await waitFor(() => {
      expect(onOpenPreLab).toHaveBeenCalledWith({
        labId: "11111111-1111-1111-1111-111111111111",
        labName: "Prompt Injection Basics",
        labSlug: "prompt-injection-basics",
        labSummary: "Practice attacking a retrieval-enabled agent.",
        labDifficulty: "medium",
      });
    });
  });

  it("renders demo mode without slug metadata and with tier buttons", async () => {
    const labs: LabCatalogItem[] = [
      {
        id: "11111111-1111-1111-1111-111111111111",
        slug: "prompt-injection-basics",
        name: "Prompt Injection Basics",
        summary: "Practice attacking a retrieval-enabled agent.",
        capabilities: {
          supports_resume: true,
          supports_uploads: false,
        },
      },
    ];
    const loadLabs = vi.fn(async () => labs);

    render(
      <LabCatalog
        apiBaseUrl="http://localhost:8000"
        learnerLabel="Demo Learner"
        mode="demo"
        loadLabs={loadLabs}
        onOpenPreLab={() => {}}
      />,
    );

    expect(
      await screen.findByRole("heading", {
        name: /Foundations of AI Agent Security/i,
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: /Foundations of AI Agent Security/i,
      }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/slug:/i)).not.toBeInTheDocument();
    expect(
      screen.queryByText(/resume: yes \| uploads: no/i),
    ).not.toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Open Module" }).length).toBe(
      8,
    );
  });

  it("renders explicit empty state when no labs are launchable", async () => {
    const loadLabs = vi.fn(async () => []);

    render(
      <LabCatalog
        apiBaseUrl="http://localhost:8000"
        learnerLabel="Demo Learner"
        loadLabs={loadLabs}
        onOpenPreLab={() => {}}
      />,
    );

    expect(
      await screen.findByText("No launchable labs are currently available."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Launch lab" }),
    ).not.toBeInTheDocument();
  });
});
