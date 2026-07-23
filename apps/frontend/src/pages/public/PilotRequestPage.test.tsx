import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import PilotRequestPage from "./PilotRequestPage";

function renderPage() {
  render(
    <MemoryRouter>
      <PilotRequestPage />
    </MemoryRouter>,
  );
}

describe("PilotRequestPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows schema validation errors without submitting invalid data", async () => {
    const requestFetch = vi.fn();
    vi.stubGlobal("fetch", requestFetch);
    renderPage();

    fireEvent.click(
      screen.getByRole("button", { name: "Submit pilot request" }),
    );

    expect(await screen.findByText("Full name is required.")).toBeVisible();
    expect(screen.getByText("Work email is required.")).toBeVisible();
    expect(screen.getByText("University is required.")).toBeVisible();
    expect(requestFetch).not.toHaveBeenCalled();
  });

  it("submits normalized form data through the lead client", async () => {
    const requestFetch = vi.fn().mockResolvedValue(Response.json({ ok: true }));
    vi.stubGlobal("fetch", requestFetch);
    renderPage();

    fireEvent.change(screen.getByLabelText("Full Name"), {
      target: { value: "  Jane Smith  " },
    });
    fireEvent.change(screen.getByLabelText("Work Email"), {
      target: { value: "  JANE@EXAMPLE.EDU  " },
    });
    fireEvent.change(screen.getByLabelText("University"), {
      target: { value: "  Example University  " },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Submit pilot request" }),
    );

    await waitFor(() => expect(requestFetch).toHaveBeenCalledOnce());
    expect(requestFetch).toHaveBeenCalledWith(
      "/api/pilot-request",
      expect.objectContaining({
        body: JSON.stringify({
          fullName: "Jane Smith",
          workEmail: "jane@example.edu",
          university: "Example University",
        }),
      }),
    );
    expect(await screen.findByText(/Request captured/)).toBeVisible();
  });
});
