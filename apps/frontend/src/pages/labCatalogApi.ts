import {
  controlPlaneRequestError,
  createControlPlaneClient,
} from "../api/client";
import type { components } from "../api/generated";
import { getCurrentAuthHeader } from "../auth/session";
import {
  AGENT_MEMORY_POISONING_LAB_ID,
  AGENT_MEMORY_POISONING_SLUG,
  AGENT_PROMPT_INJECTION_LAB_ID,
  AGENT_PROMPT_INJECTION_SLUG,
  AGENT_TOOL_MISUSE_LAB_ID,
  AGENT_TOOL_MISUSE_SLUG,
} from "../labIdentities.generated";

export type LabCatalogItem = components["schemas"]["LabCatalogItemResponse"];

const LAB_CATALOG_SOURCE = (
  import.meta.env.VITE_LAB_CATALOG_SOURCE ?? "stub"
).toLowerCase();
const PINNED_FIRST_LAB_SLUG = AGENT_PROMPT_INJECTION_SLUG;

const STUB_LABS: LabCatalogItem[] = [
  {
    id: AGENT_PROMPT_INJECTION_LAB_ID,
    slug: AGENT_PROMPT_INJECTION_SLUG,
    name: "Indirect Prompt Injection",
    summary:
      "Attack an agent using indirect prompt injection via a malicious email.",
    capabilities: {
      supports_resume: true,
      supports_uploads: false,
    },
  },
  {
    id: AGENT_TOOL_MISUSE_LAB_ID,
    slug: AGENT_TOOL_MISUSE_SLUG,
    name: "Tool Misuse",
    summary:
      "Induce an LLM agent into performing unsafe tool operations via deceptive inputs.",
    capabilities: {
      supports_resume: true,
      supports_uploads: false,
    },
  },
  {
    id: AGENT_MEMORY_POISONING_LAB_ID,
    slug: AGENT_MEMORY_POISONING_SLUG,
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
  const { data, error, response } = await createControlPlaneClient(
    apiBaseUrl,
  ).GET("/api/v1/labs", {
    params: {
      header: {
        Authorization: await getCurrentAuthHeader(),
      },
    },
  });

  if (error || !data) {
    throw controlPlaneRequestError(
      error,
      response,
      "Lab catalog request failed",
    );
  }

  return data.labs;
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

export async function createSessionForLab(
  apiBaseUrl: string,
  labId: string,
): Promise<string> {
  const { data, error, response } = await createControlPlaneClient(
    apiBaseUrl,
  ).POST("/api/v1/sessions", {
    params: {
      header: {
        Authorization: await getCurrentAuthHeader(),
        "Idempotency-Key": `frontend-create-session-${crypto.randomUUID()}`,
      },
    },
    body: {
      lab_id: labId,
    },
  });

  if (error || !data) {
    throw controlPlaneRequestError(error, response, "Session create failed");
  }

  return data.session.id;
}

export async function getLatestSessionIdForLab(
  apiBaseUrl: string,
  labId: string,
): Promise<string | null> {
  const { data, error, response } = await createControlPlaneClient(
    apiBaseUrl,
  ).GET("/api/v1/sessions", {
    params: {
      query: {
        lab_id: labId,
        limit: 1,
        sort: "created_at:desc",
      },
      header: {
        Authorization: await getCurrentAuthHeader(),
      },
    },
  });

  if (error || !data) {
    throw controlPlaneRequestError(error, response, "Session query failed");
  }

  return data.sessions[0]?.session_id ?? null;
}
