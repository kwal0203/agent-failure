import { act, fireEvent, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithQueryClient } from "../test/renderWithQueryClient";
import PreLabPage from "./PreLabPage";

const apiMocks = vi.hoisted(() => ({
  createSessionForLab: vi.fn(),
  loadLabCatalog: vi.fn(),
}));

vi.mock("./labCatalogApi", () => ({
  createSessionForLab: apiMocks.createSessionForLab,
  loadLabCatalog: apiMocks.loadLabCatalog,
}));

vi.mock("../shell/context", () => ({
  useShellBootstrap: () => ({
    apiBaseUrl: "http://localhost:8000",
    learnerLabel: "Test Learner",
    mode: "demo",
  }),
}));

const lab = {
  id: "44444444-4444-4444-4444-444444444444",
  slug: "agent-prompt-injection",
  name: "Indirect Prompt Injection",
  summary: "Summary",
  capabilities: {
    supports_resume: true,
    supports_uploads: false,
  },
};

function renderPreLabPage() {
  return renderWithQueryClient(
    <MemoryRouter
      initialEntries={[
        {
          pathname: `/labs/${lab.id}/pre-lab`,
          state: {
            labName: lab.name,
            labDifficulty: "medium",
          },
        },
      ]}
    >
      <Routes>
        <Route path="/labs/:labId/pre-lab" element={<PreLabPage />} />
        <Route
          path="/sessions/:sessionId"
          element={<p>Session destination</p>}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PreLabPage session creation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
    apiMocks.loadLabCatalog.mockResolvedValue([lab]);
  });

  it("shows mutation progress and navigates after creation succeeds", async () => {
    let resolveCreation: ((sessionId: string) => void) | undefined;
    apiMocks.createSessionForLab.mockReturnValue(
      new Promise<string>((resolve) => {
        resolveCreation = resolve;
      }),
    );
    renderPreLabPage();

    fireEvent.click(await screen.findByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Start Lab" }));

    expect(
      await screen.findByRole("button", { name: "Starting Lab..." }),
    ).toBeDisabled();
    expect(apiMocks.createSessionForLab).toHaveBeenCalledWith(
      "http://localhost:8000",
      lab.id,
      "medium",
    );

    await act(async () => {
      resolveCreation?.("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    });

    expect(await screen.findByText("Session destination")).toBeInTheDocument();
    expect(
      window.localStorage.getItem("agentfailure.latestSessionByLab"),
    ).toContain("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
  });

  it("renders the mutation error and allows another attempt", async () => {
    apiMocks.createSessionForLab.mockRejectedValue(
      new Error("Session create failed (HTTP 503)"),
    );
    renderPreLabPage();

    fireEvent.click(await screen.findByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Start Lab" }));

    expect(
      await screen.findByText("Session create failed (HTTP 503)"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start Lab" })).toBeEnabled();
  });
});
