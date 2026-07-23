import { afterEach, describe, expect, it, vi } from "vitest";
import { createPilotRequest } from "./pilotRequests";

const payload = {
  fullName: "Jane Smith",
  workEmail: "jane@example.edu",
  university: "Example University",
};

describe("createPilotRequest", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("submits leads to the same-origin Vercel Function", async () => {
    const requestFetch = vi.fn().mockResolvedValue(Response.json({ ok: true }));
    vi.stubGlobal("fetch", requestFetch);

    await createPilotRequest(payload);

    expect(requestFetch).toHaveBeenCalledWith("/api/pilot-request", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });
  });

  it("surfaces a safe endpoint error to the form", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          Response.json(
            { detail: "Pilot request service is temporarily unavailable." },
            { status: 503 },
          ),
        ),
    );

    await expect(createPilotRequest(payload)).rejects.toThrow(
      "Pilot request service is temporarily unavailable.",
    );
  });
});
