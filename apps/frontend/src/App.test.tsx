import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import App from "./App";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App shell routing", () => {
  it("routes root path to labs page", async () => {
    renderAt("/");

    expect(await screen.findByRole("heading", { name: "Labs" })).toBeInTheDocument();
    expect(screen.getByText(/Demo shell is active for/i)).toBeInTheDocument();
  });

  it("renders history page inside shell nav", async () => {
    renderAt("/history");

    expect(await screen.findByRole("heading", { name: "History" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Labs" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Trace" })).toBeInTheDocument();
  });

  it("redirects unknown route to labs", async () => {
    renderAt("/missing/path");

    expect(await screen.findByRole("heading", { name: "Labs" })).toBeInTheDocument();
  });
});
