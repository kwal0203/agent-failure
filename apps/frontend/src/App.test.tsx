import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const AUTH_USER_STORAGE_KEY = "agentfailure.auth.user";
const AUTH_TOKEN_STORAGE_KEY = "agentfailure.auth.tokens";

function makeIdToken(email: string) {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const payload = btoa(
    JSON.stringify({
      sub: "user-123",
      email,
      preferred_username: email.split("@")[0],
    }),
  );
  return `${header}.${payload}.signature`;
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App routing with auth guards", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    window.sessionStorage.clear();
    vi.stubEnv("VITE_COGNITO_CLIENT_ID", "test-client-id");
    vi.stubEnv("VITE_COGNITO_USER_POOL_ID", "us-east-2_testpool");
  });

  it("redirects root to login", async () => {
    renderAt("/");

    expect(
      await screen.findByRole("heading", {
        name: "AgentFailure",
      }),
    ).toBeInTheDocument();
  });

  it("redirects protected routes to login when signed out", async () => {
    renderAt("/labs");

    expect(
      await screen.findByRole("heading", { name: "AgentFailure" }),
    ).toBeInTheDocument();
  });

  it("redirects authenticated user away from login to app", async () => {
    window.sessionStorage.setItem(
      AUTH_USER_STORAGE_KEY,
      JSON.stringify({ id: "kane", email: "kane@example.com", label: "kane" }),
    );
    window.sessionStorage.setItem(
      AUTH_TOKEN_STORAGE_KEY,
      JSON.stringify({
        accessToken: "access-token",
        idToken: makeIdToken("kane@example.com"),
        refreshToken: null,
        expiresAtEpochSec: Math.floor(Date.now() / 1000) + 3600,
      }),
    );

    renderAt("/login");

    expect(
      await screen.findByRole("heading", { name: "Labs" }),
    ).toBeInTheDocument();
  });

  it("renders protected labs route when signed in", async () => {
    window.sessionStorage.setItem(
      AUTH_USER_STORAGE_KEY,
      JSON.stringify({ id: "kane", email: "kane@example.com", label: "kane" }),
    );
    window.sessionStorage.setItem(
      AUTH_TOKEN_STORAGE_KEY,
      JSON.stringify({
        accessToken: "access-token",
        idToken: makeIdToken("kane@example.com"),
        refreshToken: null,
        expiresAtEpochSec: Math.floor(Date.now() / 1000) + 3600,
      }),
    );

    renderAt("/labs");

    expect(
      await screen.findByRole("heading", { name: "Labs" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Cyberrange Demo Surface/i)).toBeInTheDocument();
  });

  it("blocks invalid login input client-side", async () => {
    renderAt("/login");

    fireEvent.click(await screen.findByRole("button", { name: "Sign In" }));

    expect(
      await screen.findByText("Email and password are required."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "AgentFailure" }),
    ).toBeInTheDocument();
  });

  it("logs in and redirects to next path when provided", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        text: async () =>
          JSON.stringify({
            AuthenticationResult: {
              AccessToken: "access-token",
              IdToken: makeIdToken("kane@example.com"),
              ExpiresIn: 3600,
            },
          }),
      })),
    );

    renderAt("/login?next=%2Flabs");

    fireEvent.change(await screen.findByLabelText("Email Address"), {
      target: { value: "kane@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    expect(
      await screen.findByRole("heading", { name: "Labs" }),
    ).toBeInTheDocument();
  });

  it("rejects unknown login credentials", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        text: async () => JSON.stringify({ message: "Invalid credentials" }),
      })),
    );

    renderAt("/login");

    fireEvent.change(await screen.findByLabelText("Email Address"), {
      target: { value: "kaneeeee@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    expect(await screen.findByText("Invalid credentials")).toBeInTheDocument();
  });
});
