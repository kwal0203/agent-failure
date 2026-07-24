import { beforeEach, describe, expect, it, vi } from "vitest";
import { getAmplifySession } from "./amplifyAuth";
import { getCurrentAccessToken, getCurrentAuthHeader } from "./session";

vi.mock("./amplifyAuth", () => ({
  getAmplifySession: vi.fn(),
}));

describe("Amplify-backed auth session", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("asks Amplify for the current session on every token request", async () => {
    vi.mocked(getAmplifySession)
      .mockResolvedValueOnce({
        tokens: {
          accessToken: {
            toString: () => "first-token",
            payload: {},
          },
        },
      })
      .mockResolvedValueOnce({
        tokens: {
          accessToken: {
            toString: () => "refreshed-token",
            payload: {},
          },
        },
      });

    await expect(getCurrentAccessToken()).resolves.toBe("first-token");
    await expect(getCurrentAuthHeader()).resolves.toBe(
      "Bearer refreshed-token",
    );
    expect(getAmplifySession).toHaveBeenCalledTimes(2);
  });

  it("rejects requests without an authenticated access token", async () => {
    vi.mocked(getAmplifySession).mockResolvedValue({ tokens: undefined });

    await expect(getCurrentAccessToken()).rejects.toThrow(
      "No active access token",
    );
  });
});
