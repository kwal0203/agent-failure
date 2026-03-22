import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LabCatalog, type LabCatalogItem } from "./LabsPage";

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
    const createSession = vi.fn(async () => "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    const onOpenSession = vi.fn();

    render(
      <LabCatalog
        apiBaseUrl="http://localhost:8000"
        learnerLabel="Demo Learner"
        loadLabs={loadLabs}
        createSession={createSession}
        onOpenSession={onOpenSession}
      />,
    );

    expect(await screen.findByRole("heading", { name: "Prompt Injection Basics" })).toBeInTheDocument();
    expect(screen.getByText(/slug:/i)).toBeInTheDocument();
    expect(screen.getByText(/resume: yes \| uploads: no/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Launch lab" }));

    expect(createSession).toHaveBeenCalledWith(
      "http://localhost:8000",
      "11111111-1111-1111-1111-111111111111",
    );
    await waitFor(() => {
      expect(onOpenSession).toHaveBeenCalledWith("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    });
  });

  it("renders explicit empty state when no labs are launchable", async () => {
    const loadLabs = vi.fn(async () => []);

    render(
      <LabCatalog
        apiBaseUrl="http://localhost:8000"
        learnerLabel="Demo Learner"
        loadLabs={loadLabs}
        onOpenSession={() => {}}
      />,
    );

    expect(
      await screen.findByText("No launchable labs are currently available."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Launch lab" })).not.toBeInTheDocument();
  });
});
