import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import App from "./App";

const AUTH_STORAGE_KEY = "agent_failure_auth_user";

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App routing with auth guards", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("renders public home at root", async () => {
    renderAt("/");

    expect(
      await screen.findByRole("heading", {
        name: "Learn AI Agent Security Through Hands-On Labs",
      }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Get Started" })).toHaveAttribute(
      "href",
      "/signup",
    );
  });

  it("redirects protected routes to login when signed out", async () => {
    renderAt("/labs");

    expect(
      await screen.findByRole("heading", { name: "Log In" }),
    ).toBeInTheDocument();
  });

  it("redirects authenticated user away from login to app", async () => {
    window.localStorage.setItem(
      AUTH_STORAGE_KEY,
      JSON.stringify({ id: "kane", email: "kane@example.com", label: "kane" }),
    );

    renderAt("/login");

    expect(
      await screen.findByRole("heading", { name: "Platform Home" }),
    ).toBeInTheDocument();
  });

  it("renders protected labs route when signed in", async () => {
    window.localStorage.setItem(
      AUTH_STORAGE_KEY,
      JSON.stringify({ id: "kane", email: "kane@example.com", label: "kane" }),
    );

    renderAt("/labs");

    expect(
      await screen.findByRole("heading", { name: "Labs" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Cyberrange Demo Surface/i)).toBeInTheDocument();
  });

  it("blocks invalid login input client-side", async () => {
    renderAt("/login");

    fireEvent.click(await screen.findByRole("button", { name: "Log In" }));

    expect(
      await screen.findByText("Email or username is required."),
    ).toBeInTheDocument();
    expect(screen.getByText("Password is required.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Log In" })).toBeInTheDocument();
  });

  it("logs in and redirects to next path when provided", async () => {
    renderAt("/login?next=%2Flabs");

    fireEvent.change(await screen.findByLabelText("Email or Username"), {
      target: { value: "kane" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Log In" }));

    expect(
      await screen.findByRole("heading", { name: "Labs" }),
    ).toBeInTheDocument();
  });

  it("rejects unknown login credentials", async () => {
    renderAt("/login");

    fireEvent.change(await screen.findByLabelText("Email or Username"), {
      target: { value: "kaneeeee" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Log In" }));

    expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
  });
});
