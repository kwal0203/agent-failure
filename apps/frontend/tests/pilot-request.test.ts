import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { handleRequest } from "../api/pilot-request";

const validLead = {
  fullName: "Jane Smith",
  workEmail: "jane@example.edu",
  university: "Example University",
  courseName: "CYB 401",
  notes: "Planning a cohort of 30 students.",
};

function makeRequest(
  body: unknown = validLead,
  origin = "https://www.agentfailure.com",
): Request {
  return new Request("https://www.agentfailure.com/api/pilot-request", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: origin,
    },
    body: JSON.stringify(body),
  });
}

describe("pilot request Vercel Function", () => {
  beforeEach(() => {
    vi.stubEnv("RESEND_API_KEY", "re_test");
    vi.stubEnv(
      "PILOT_LEAD_FROM",
      "Agent Failure <leads@auth.agentfailure.com>",
    );
    vi.stubEnv("PILOT_LEAD_TO", "owner@example.com");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("sends a validated lead through Resend", async () => {
    const resendFetch = vi
      .fn()
      .mockResolvedValue(Response.json({ id: "email-123" }));
    vi.stubGlobal("fetch", resendFetch);

    const response = await handleRequest(makeRequest());

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ ok: true });
    expect(resendFetch).toHaveBeenCalledOnce();

    const [url, init] = resendFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("https://api.resend.com/emails");
    expect(init.headers).toMatchObject({
      Authorization: "Bearer re_test",
      "Content-Type": "application/json",
    });
    expect(init.signal).toBeInstanceOf(AbortSignal);

    const email = JSON.parse(String(init.body)) as Record<string, unknown>;
    expect(email).toMatchObject({
      from: "Agent Failure <leads@auth.agentfailure.com>",
      to: ["owner@example.com"],
      reply_to: "jane@example.edu",
      subject: "New Agent Failure pilot request — Example University",
    });
    expect(email.text).toContain("Planning a cohort of 30 students.");
  });

  it("rejects invalid lead details without calling Resend", async () => {
    const resendFetch = vi.fn();
    vi.stubGlobal("fetch", resendFetch);

    const response = await handleRequest(
      makeRequest({ ...validLead, workEmail: "not-an-email" }),
    );

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      detail: "Enter a valid work email.",
    });
    expect(resendFetch).not.toHaveBeenCalled();
  });

  it("silently accepts honeypot submissions without sending email", async () => {
    const resendFetch = vi.fn();
    vi.stubGlobal("fetch", resendFetch);

    const response = await handleRequest(
      makeRequest({ ...validLead, website: "https://spam.example" }),
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ ok: true });
    expect(resendFetch).not.toHaveBeenCalled();
  });

  it("does not report success when Resend rejects the email", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          Response.json({ message: "Rejected" }, { status: 422 }),
        ),
    );

    const response = await handleRequest(makeRequest());

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({
      detail: "We could not submit your request. Please try again.",
    });
  });

  it("does not report success when Resend is unreachable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("Network error")),
    );

    const response = await handleRequest(makeRequest());

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({
      detail: "We could not submit your request. Please try again.",
    });
  });

  it("rejects browser submissions from an unexpected origin", async () => {
    const resendFetch = vi.fn();
    vi.stubGlobal("fetch", resendFetch);

    const response = await handleRequest(
      makeRequest(validLead, "https://malicious.example"),
    );

    expect(response.status).toBe(403);
    expect(resendFetch).not.toHaveBeenCalled();
  });
});
