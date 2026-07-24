import {
  controlPlaneRequestError,
  createControlPlaneClient,
} from "../api/client";
import type { components } from "../api/generated";
import { getCurrentAuthHeader } from "../auth/session";

export type LabCatalogItem = components["schemas"]["LabCatalogItemResponse"];

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
