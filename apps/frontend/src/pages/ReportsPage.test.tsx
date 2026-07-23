import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ReportsPage from "./ReportsPage";

const loadLabCatalogMock = vi.fn();
const getLatestSessionIdForLabMock = vi.fn();

vi.mock("../auth/useAuth", () => ({
  useAuth: () => ({
    logout: vi.fn(),
  }),
}));

vi.mock("../shell/context", () => ({
  useShellBootstrap: () => ({
    apiBaseUrl: "http://localhost:8000",
    mode: "demo",
  }),
}));

vi.mock("./labCatalogApi", () => ({
  loadLabCatalog: (...args: unknown[]) => loadLabCatalogMock(...args),
  getLatestSessionIdForLab: (...args: unknown[]) =>
    getLatestSessionIdForLabMock(...args),
}));

describe("ReportsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    loadLabCatalogMock.mockResolvedValue([
      {
        id: "44444444-4444-4444-4444-444444444444",
        slug: "agent-prompt-injection",
        name: "Indirect Prompt Injection",
        summary: "summary",
        capabilities: { supports_resume: true, supports_uploads: false },
      },
      {
        id: "55555555-5555-5555-5555-555555555555",
        slug: "agent-tool-misuse",
        name: "Tool Misuse",
        summary: "summary",
        capabilities: { supports_resume: true, supports_uploads: false },
      },
      {
        id: "66666666-6666-6666-6666-666666666666",
        slug: "agent-memory-poisoning",
        name: "Memory Poisoning",
        summary: "summary",
        capabilities: { supports_resume: true, supports_uploads: false },
      },
    ]);
  });

  it("keeps Open Report disabled when no latest session exists", async () => {
    getLatestSessionIdForLabMock.mockResolvedValue(null);

    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(loadLabCatalogMock).toHaveBeenCalled();
    });

    const buttons = await screen.findAllByRole("button", {
      name: /open report/i,
    });
    expect(buttons.length).toBeGreaterThan(0);
    expect(buttons[0]).toBeDisabled();
  });

  it("enables Open Report when latest session exists", async () => {
    getLatestSessionIdForLabMock.mockImplementation(
      async (_apiBaseUrl: string, labId: string) =>
        labId === "44444444-4444-4444-4444-444444444444"
          ? "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
          : null,
    );

    render(
      <MemoryRouter>
        <ReportsPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      const buttons = screen.getAllByRole("button", { name: /open report/i });
      expect(buttons.some((button) => !button.hasAttribute("disabled"))).toBe(
        true,
      );
    });
  });
});
