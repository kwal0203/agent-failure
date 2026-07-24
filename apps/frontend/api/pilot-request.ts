import { type PilotLead, pilotLeadSchema } from "../src/schemas/pilotRequest";

const RESEND_EMAILS_URL = "https://api.resend.com/emails";
const MAX_REQUEST_BYTES = 20_000;

function jsonResponse(body: unknown, status: number): Response {
  return Response.json(body, {
    status,
    headers: {
      "Cache-Control": "no-store",
    },
  });
}

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function line(label: string, value: string | number | undefined): string {
  return `${label}: ${value ?? "Not provided"}`;
}

function buildText(lead: PilotLead): string {
  return [
    "A new university pilot request was submitted.",
    "",
    line("Name", lead.fullName),
    line("Work email", lead.workEmail),
    line("University", lead.university),
    line("Role", lead.role),
    line("Course", lead.courseName),
    line("Cohort size", lead.cohortSize),
    "",
    "Notes:",
    lead.notes ?? "Not provided",
  ].join("\n");
}

function buildHtml(lead: PilotLead): string {
  const fields: Array<[string, string | number | undefined]> = [
    ["Name", lead.fullName],
    ["Work email", lead.workEmail],
    ["University", lead.university],
    ["Role", lead.role],
    ["Course", lead.courseName],
    ["Cohort size", lead.cohortSize],
  ];
  const rows = fields
    .map(
      ([label, value]) =>
        `<tr><th align="left" style="padding:4px 12px 4px 0">${escapeHtml(label)}</th><td style="padding:4px 0">${escapeHtml(String(value ?? "Not provided"))}</td></tr>`,
    )
    .join("");

  return [
    "<h1>New university pilot request</h1>",
    "<table>",
    rows,
    "</table>",
    "<h2>Notes</h2>",
    `<p style="white-space:pre-wrap">${escapeHtml(lead.notes ?? "Not provided")}</p>`,
  ].join("");
}

function allowedOrigin(request: Request): boolean {
  const origin = request.headers.get("origin");
  if (!origin) return true;

  const configured = (process.env.PILOT_ALLOWED_ORIGINS ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const defaults = [
    "https://agentfailure.com",
    "https://www.agentfailure.com",
    "http://localhost:5173",
  ];
  const previewOrigin = process.env.VERCEL_URL
    ? `https://${process.env.VERCEL_URL}`
    : null;

  return [...configured, ...defaults, previewOrigin].some(
    (candidate) => candidate === origin,
  );
}

async function parseRequestBody(request: Request): Promise<unknown> {
  const declaredLength = Number(request.headers.get("content-length") ?? "0");
  if (declaredLength > MAX_REQUEST_BYTES) {
    throw new Error("REQUEST_TOO_LARGE");
  }

  const rawBody = await request.text();
  if (rawBody.length > MAX_REQUEST_BYTES) {
    throw new Error("REQUEST_TOO_LARGE");
  }
  return JSON.parse(rawBody);
}

async function handleRequest(request: Request): Promise<Response> {
  if (request.method !== "POST") {
    return new Response("Method Not Allowed", {
      status: 405,
      headers: { Allow: "POST" },
    });
  }

  if (!allowedOrigin(request)) {
    return jsonResponse({ detail: "Origin not allowed." }, 403);
  }

  let requestBody: unknown;
  try {
    requestBody = await parseRequestBody(request);
  } catch (error) {
    const detail =
      error instanceof Error && error.message === "REQUEST_TOO_LARGE"
        ? "Request body is too large."
        : "Invalid JSON body.";
    return jsonResponse({ detail }, 400);
  }

  const validation = pilotLeadSchema.safeParse(requestBody);
  if (!validation.success) {
    return jsonResponse(
      {
        detail: validation.error.issues[0]?.message ?? "Invalid request body.",
      },
      400,
    );
  }

  // Silently accept honeypot submissions so bots do not learn how to bypass it.
  if (validation.data.website) {
    return jsonResponse({ ok: true }, 200);
  }

  const apiKey = process.env.RESEND_API_KEY;
  const from = process.env.PILOT_LEAD_FROM;
  const to = process.env.PILOT_LEAD_TO;
  const recipients = (to ?? "")
    .split(",")
    .map((address) => address.trim())
    .filter(Boolean);
  if (!apiKey || !from || recipients.length === 0) {
    console.error("Pilot lead email service is not configured.");
    return jsonResponse(
      { detail: "Pilot request service is temporarily unavailable." },
      503,
    );
  }

  let resendResponse: Response;
  try {
    resendResponse = await fetch(RESEND_EMAILS_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from,
        to: recipients,
        reply_to: validation.data.workEmail,
        subject: `New Agent Failure pilot request — ${validation.data.university.replaceAll(/[\r\n]/g, " ")}`,
        text: buildText(validation.data),
        html: buildHtml(validation.data),
        tags: [{ name: "source", value: "pilot-request" }],
      }),
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    console.error("Resend pilot lead request failed.");
    return jsonResponse(
      { detail: "We could not submit your request. Please try again." },
      502,
    );
  }

  if (!resendResponse.ok) {
    console.error(
      `Resend rejected pilot lead email (${resendResponse.status}).`,
    );
    return jsonResponse(
      { detail: "We could not submit your request. Please try again." },
      502,
    );
  }

  return jsonResponse({ ok: true }, 200);
}

export default {
  fetch: handleRequest,
};

export { handleRequest };
