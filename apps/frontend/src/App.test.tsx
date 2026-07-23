import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const PENDING_ENROLLMENT_TOKEN_KEY = "agentfailure.auth.pendingEnrollmentToken";
const ENROLLMENT_REDEEM_ERROR_KEY = "agentfailure.auth.enrollmentRedeemError";

const amplifyAuthMocks = vi.hoisted(() => ({
  getAmplifySession: vi.fn(),
  getAmplifyUser: vi.fn(),
  signInWithAmplify: vi.fn(),
  signOutWithAmplify: vi.fn(),
  signUpWithAmplify: vi.fn(),
  confirmSignUpWithAmplify: vi.fn(),
  requestPasswordResetWithAmplify: vi.fn(),
  confirmPasswordResetWithAmplify: vi.fn(),
}));

vi.mock("./auth/amplifyAuth", () => amplifyAuthMocks);

function mockAuthenticatedUser(email = "kane@example.com") {
  amplifyAuthMocks.getAmplifyUser.mockResolvedValue({
    userId: "user-123",
    username: email,
    signInDetails: { loginId: email },
  });
  amplifyAuthMocks.getAmplifySession.mockResolvedValue({
    tokens: {
      accessToken: {
        toString: () => "access-token",
        payload: {},
      },
      idToken: {
        toString: () => "id-token",
        payload: {
          sub: "user-123",
          email,
          preferred_username: email.split("@")[0],
        },
      },
    },
  });
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
    vi.resetAllMocks();
    vi.unstubAllGlobals();
    window.sessionStorage.clear();
    vi.stubEnv("VITE_COGNITO_CLIENT_ID", "test-client-id");
    vi.stubEnv("VITE_COGNITO_USER_POOL_ID", "us-east-2_testpool");
    vi.stubEnv("VITE_ENROLLMENT_API_ENABLED", "false");
    amplifyAuthMocks.getAmplifyUser.mockRejectedValue(
      new Error("User is not authenticated"),
    );
    amplifyAuthMocks.getAmplifySession.mockRejectedValue(
      new Error("User is not authenticated"),
    );
    amplifyAuthMocks.signOutWithAmplify.mockResolvedValue(undefined);
  });

  it("redirects root to login", async () => {
    renderAt("/");

    expect(
      await screen.findByRole("heading", {
        name: "Sign in",
      }),
    ).toBeInTheDocument();
  });

  it("redirects protected routes to login when signed out", async () => {
    renderAt("/labs");

    expect(
      await screen.findByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
  });

  it("redirects authenticated user away from login to app", async () => {
    mockAuthenticatedUser();

    renderAt("/login");

    expect(
      await screen.findByRole("heading", {
        name: /Foundations of AI Agent Security/i,
      }),
    ).toBeInTheDocument();
  });

  it("renders protected labs route when signed in", async () => {
    mockAuthenticatedUser();

    renderAt("/labs");

    expect(
      await screen.findByRole("heading", {
        name: /Foundations of AI Agent Security/i,
      }),
    ).toBeInTheDocument();
  });

  it("redirects authenticated users to enrollment when pending token exists", async () => {
    vi.stubEnv("VITE_ENROLLMENT_API_ENABLED", "true");
    mockAuthenticatedUser();
    window.sessionStorage.setItem(
      PENDING_ENROLLMENT_TOKEN_KEY,
      "pending-token",
    );

    renderAt("/labs");

    expect(
      await screen.findByRole("heading", {
        name: "Complete Course Enrollment",
      }),
    ).toBeInTheDocument();
  });

  it("redirects authenticated users to enrollment when redemption error exists", async () => {
    vi.stubEnv("VITE_ENROLLMENT_API_ENABLED", "true");
    mockAuthenticatedUser();
    window.sessionStorage.setItem(
      ENROLLMENT_REDEEM_ERROR_KEY,
      "Token expired or already redeemed",
    );

    renderAt("/labs");

    expect(
      await screen.findByRole("heading", {
        name: "Complete Course Enrollment",
      }),
    ).toBeInTheDocument();
  });

  it("blocks invalid login input client-side", async () => {
    renderAt("/login");

    fireEvent.click(await screen.findByRole("button", { name: "Sign In" }));

    expect(
      await screen.findByText("Email and password are required."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Sign in" }),
    ).toBeInTheDocument();
  });

  it("logs in and redirects to next path when provided", async () => {
    amplifyAuthMocks.signInWithAmplify.mockImplementation(async () => {
      mockAuthenticatedUser();
      return {
        isSignedIn: true,
        nextStep: { signInStep: "DONE" },
      };
    });

    renderAt("/login?next=%2Flabs");

    fireEvent.change(await screen.findByLabelText("Email Address"), {
      target: { value: "kane@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    expect(
      await screen.findByRole("heading", {
        name: /Foundations of AI Agent Security/i,
      }),
    ).toBeInTheDocument();
    expect(amplifyAuthMocks.signInWithAmplify).toHaveBeenCalledWith(
      "kane@example.com",
      "password123",
    );
  });

  it("rejects unknown login credentials", async () => {
    amplifyAuthMocks.signInWithAmplify.mockRejectedValue(
      new Error("Invalid credentials"),
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
