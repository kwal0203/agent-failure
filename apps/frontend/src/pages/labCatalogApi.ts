import type {
  GetLabsResponse,
  GetSessionsResponse,
  LabCatalogItemResponse,
} from "../../../contracts/ts/index";
import { getCurrentAuthHeader } from "../auth/session";

export type LabDifficulty = "easy" | "medium";
export type LabCatalogItem = LabCatalogItemResponse;

const LAB_CATALOG_SOURCE = (
  import.meta.env.VITE_LAB_CATALOG_SOURCE ?? "stub"
).toLowerCase();
const PINNED_FIRST_LAB_SLUG = "agent-prompt-injection";

const STUB_LABS: LabCatalogItem[] = [
  {
    id: "44444444-4444-4444-4444-444444444444",
    slug: "agent-prompt-injection",
    name: "Indirect Prompt Injection",
    summary:
      "Attack an agent using indirect prompt injection via a malicious email.",
    capabilities: {
      supports_resume: true,
      supports_uploads: false,
    },
  },
  {
    id: "55555555-5555-5555-5555-555555555555",
    slug: "agent-tool-misuse",
    name: "Tool Misuse",
    summary:
      "Induce an LLM agent into performing unsafe tool operations via deceptive inputs.",
    capabilities: {
      supports_resume: true,
      supports_uploads: false,
    },
  },
  {
    id: "66666666-6666-6666-6666-666666666666",
    slug: "agent-memory-poisoning",
    name: "Memory Poisoning",
    summary:
      "Poison an LLM agent's memory to reroute invoice payments to an attacker-controlled account.",
    capabilities: {
      supports_resume: true,
      supports_uploads: false,
    },
  },
];

async function fetchLabsFromApi(apiBaseUrl: string): Promise<LabCatalogItem[]> {
  const response = await fetch(`${apiBaseUrl}/api/v1/labs`, {
    method: "GET",
    headers: {
      Authorization: await getCurrentAuthHeader(),
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Lab catalog request failed (HTTP ${response.status})`);
  }

  const payload = (await response.json()) as GetLabsResponse;
  const rawLabs = payload.labs;
  if (!Array.isArray(rawLabs)) {
    throw new Error("Lab catalog response has invalid labs[] shape");
  }

  return rawLabs
    .filter((item): item is LabCatalogItem => {
      if (typeof item !== "object" || item === null) {
        return false;
      }
      if (
        !("id" in item) ||
        !("slug" in item) ||
        !("name" in item) ||
        !("summary" in item) ||
        !("capabilities" in item)
      ) {
        return false;
      }

      const capabilities = item.capabilities;
      return (
        typeof item.id === "string" &&
        typeof item.slug === "string" &&
        typeof item.name === "string" &&
        typeof item.summary === "string" &&
        typeof capabilities === "object" &&
        capabilities !== null &&
        "supports_resume" in capabilities &&
        "supports_uploads" in capabilities &&
        typeof capabilities.supports_resume === "boolean" &&
        typeof capabilities.supports_uploads === "boolean"
      );
    })
    .map((item) => ({
      id: item.id,
      slug: item.slug,
      name: item.name,
      summary: item.summary,
      capabilities: {
        supports_resume: item.capabilities.supports_resume,
        supports_uploads: item.capabilities.supports_uploads,
      },
    }));
}

function normalizeLabCatalog(labs: LabCatalogItem[]): LabCatalogItem[] {
  const pinnedIndex = labs.findIndex(
    (lab) => lab.slug === PINNED_FIRST_LAB_SLUG,
  );
  if (pinnedIndex <= 0) {
    return labs;
  }
  const pinned = labs[pinnedIndex];
  const rest = labs.filter((_, index) => index !== pinnedIndex);
  return [pinned, ...rest];
}

export async function loadLabCatalog(
  apiBaseUrl: string,
): Promise<LabCatalogItem[]> {
  if (LAB_CATALOG_SOURCE === "empty") {
    return [];
  }

  if (LAB_CATALOG_SOURCE === "api") {
    const labs = await fetchLabsFromApi(apiBaseUrl);
    return normalizeLabCatalog(labs);
  }

  return normalizeLabCatalog(STUB_LABS);
}

function extractSessionId(payload: unknown): string | undefined {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "session" in payload &&
    typeof payload.session === "object" &&
    payload.session !== null &&
    "id" in payload.session &&
    typeof payload.session.id === "string"
  ) {
    return payload.session.id;
  }
  if (
    typeof payload === "object" &&
    payload !== null &&
    "id" in payload &&
    typeof payload.id === "string"
  ) {
    return payload.id;
  }
  return undefined;
}

export async function createSessionForLab(
  apiBaseUrl: string,
  labId: string,
  labDifficulty: LabDifficulty = "medium",
): Promise<string> {
  const response = await fetch(`${apiBaseUrl}/api/v1/sessions`, {
    method: "POST",
    headers: {
      Authorization: await getCurrentAuthHeader(),
      "Idempotency-Key": `frontend-create-session-${crypto.randomUUID()}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      lab_id: labId,
      lab_difficulty: labDifficulty,
    }),
  });

  if (!response.ok) {
    throw new Error(`Session create failed (HTTP ${response.status})`);
  }

  const payload = (await response.json()) as unknown;
  const sessionId = extractSessionId(payload);
  if (!sessionId) {
    throw new Error(
      "Session create succeeded but response did not include session id",
    );
  }

  return sessionId;
}

export async function getLatestSessionIdForLab(
  apiBaseUrl: string,
  labId: string,
): Promise<string | null> {
  const params = new URLSearchParams({
    lab_id: labId,
    limit: "1",
    sort: "created_at:desc",
  });
  const response = await fetch(`${apiBaseUrl}/api/v1/sessions?${params}`, {
    method: "GET",
    headers: {
      Authorization: await getCurrentAuthHeader(),
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Session query failed (HTTP ${response.status})`);
  }

  const payload = (await response.json()) as GetSessionsResponse;
  const first = Array.isArray(payload.sessions)
    ? payload.sessions[0]
    : undefined;
  if (
    !first ||
    typeof first.session_id !== "string" ||
    first.session_id.length < 1
  ) {
    return null;
  }
  return first.session_id;
}
