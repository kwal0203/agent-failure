export type LabDifficulty = "easy" | "medium";

export type LabCatalogItem = {
  id: string;
  slug: string;
  name: string;
  summary: string;
  capabilities: {
    supports_resume: boolean;
    supports_uploads: boolean;
  };
};

const LAB_CATALOG_SOURCE = (
  import.meta.env.VITE_LAB_CATALOG_SOURCE ?? "stub"
).toLowerCase();

const STUB_LABS: LabCatalogItem[] = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    slug: "prompt-injection",
    name: "Indirect Prompt Injection",
    summary:
      "Practice indirect prompt-injection attack patterns against a baseline runtime.",
    capabilities: {
      supports_resume: true,
      supports_uploads: false,
    },
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    slug: "tool-misuse",
    name: "Tool Misuse",
    summary: "Identify unsafe tool invocation paths and guardrail failures.",
    capabilities: {
      supports_resume: true,
      supports_uploads: false,
    },
  },
  {
    id: "33333333-3333-3333-3333-333333333333",
    slug: "rag-poisoning",
    name: "RAG Poisoning",
    summary: "Explore retrieval poisoning behaviors and mitigation workflows.",
    capabilities: {
      supports_resume: true,
      supports_uploads: false,
    },
  },
  {
    id: "44444444-4444-4444-4444-444444444444",
    slug: "agent-prompt-injection",
    name: "Agent: Indirect Prompt Injection",
    summary:
      "Attack an LLM agent with indirect prompt injection via a crafted inbox email.",
    capabilities: {
      supports_resume: true,
      supports_uploads: false,
    },
  },
  {
    id: "55555555-5555-5555-5555-555555555555",
    slug: "agent-tool-misuse",
    name: "Agent: Tool Misuse",
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
    name: "Agent: Memory Poisoning",
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
      Authorization: "Bearer local:kane:learner",
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error(`Lab catalog request failed (HTTP ${response.status})`);
  }

  const payload = (await response.json()) as unknown;
  if (typeof payload !== "object" || payload === null || !("labs" in payload)) {
    throw new Error("Lab catalog response did not include labs[]");
  }

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

export async function loadLabCatalog(
  apiBaseUrl: string,
): Promise<LabCatalogItem[]> {
  if (LAB_CATALOG_SOURCE === "empty") {
    return [];
  }

  if (LAB_CATALOG_SOURCE === "api") {
    return fetchLabsFromApi(apiBaseUrl);
  }

  return STUB_LABS;
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
      Authorization: "Bearer local:kane:learner",
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
