import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useShellBootstrap } from "../shell/context";

const LAB_CATALOG_SOURCE = (
  import.meta.env.VITE_LAB_CATALOG_SOURCE ?? "stub"
).toLowerCase();

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

const STUB_LABS: LabCatalogItem[] = [
  {
    id: "11111111-1111-1111-1111-111111111111",
    slug: "prompt-injection",
    name: "Prompt Injection",
    summary: "Practice prompt-injection attack patterns against a baseline runtime.",
    capabilities: {
      supports_resume: true,
      supports_uploads: false,
    },
  },
  {
    id: "22222222-2222-2222-2222-222222222222",
    slug: "rag-poisoning",
    name: "RAG Poisoning",
    summary: "Explore retrieval poisoning behaviors and mitigation workflows.",
    capabilities: {
      supports_resume: true,
      supports_uploads: false,
    },
  },
  {
    id: "33333333-3333-3333-3333-333333333333",
    slug: "tool-misuse",
    name: "Tool Misuse",
    summary: "Identify unsafe tool invocation paths and guardrail failures.",
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

export async function loadLabCatalog(apiBaseUrl: string): Promise<LabCatalogItem[]> {
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
    }),
  });

  if (!response.ok) {
    throw new Error(`Session create failed (HTTP ${response.status})`);
  }

  const payload = (await response.json()) as unknown;
  const sessionId = extractSessionId(payload);
  if (!sessionId) {
    throw new Error("Session create succeeded but response did not include session id");
  }

  return sessionId;
}

type LabCatalogProps = {
  apiBaseUrl: string;
  learnerLabel: string;
  loadLabs?: (apiBaseUrl: string) => Promise<LabCatalogItem[]>;
  createSession?: (apiBaseUrl: string, labId: string) => Promise<string>;
  onOpenSession: (sessionId: string) => void;
};

export function LabCatalog({
  apiBaseUrl,
  learnerLabel,
  loadLabs = loadLabCatalog,
  createSession = createSessionForLab,
  onOpenSession,
}: LabCatalogProps) {
  const [labs, setLabs] = useState<LabCatalogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [creatingLabId, setCreatingLabId] = useState<string | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);

  const refreshLabs = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const loadedLabs = await loadLabs(apiBaseUrl);
      setLabs(loadedLabs);
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : "Failed to load lab catalog");
      setLabs([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void refreshLabs();
  }, [apiBaseUrl]);

  const launchLab = async (labId: string) => {
    setCreatingLabId(labId);
    setCreateError(null);
    try {
      const sessionId = await createSession(apiBaseUrl, labId);
      onOpenSession(sessionId);
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : "Session create failed");
    } finally {
      setCreatingLabId(null);
    }
  };

  return (
    <section>
      <h1 style={{ margin: "0 0 12px" }}>Labs</h1>
      <p style={{ margin: "0 0 14px" }}>
        Demo shell is active for <strong>{learnerLabel}</strong>.
      </p>

      {isLoading && <p style={{ margin: "0 0 12px" }}>Loading lab catalog...</p>}

      {loadError && (
        <div
          style={{
            border: "1px solid #fecaca",
            background: "#fff1f2",
            borderRadius: 10,
            padding: 12,
            marginBottom: 12,
            maxWidth: 800,
          }}
        >
          <p style={{ margin: "0 0 8px", color: "#9f1239" }}>Error: {loadError}</p>
          <button type="button" onClick={() => void refreshLabs()}>
            Retry
          </button>
        </div>
      )}

      {!isLoading && !loadError && labs.length === 0 && (
        <div
          style={{
            border: "1px solid #cdd5e2",
            borderRadius: 10,
            background: "#fff",
            padding: 16,
            maxWidth: 800,
          }}
        >
          <p style={{ margin: 0 }}>No launchable labs are currently available.</p>
        </div>
      )}

      {!isLoading && !loadError && labs.length > 0 && (
        <div
          style={{
            display: "grid",
            gap: 12,
            maxWidth: 900,
            margin: "0 auto",
          }}
        >
          {labs.map((lab) => {
            const isCreatingThisLab = creatingLabId === lab.id;
            return (
              <article
                key={lab.id}
                style={{
                  border: "1px solid #cdd5e2",
                  borderRadius: 10,
                  background: "#fff",
                  padding: 16,
                  textAlign: "left",
                }}
              >
                <h2 style={{ margin: "0 0 8px", fontSize: 20 }}>{lab.name}</h2>
                <p style={{ margin: "0 0 8px", opacity: 0.9 }}>{lab.summary}</p>
                <p style={{ margin: "0 0 10px", fontSize: 13, opacity: 0.8 }}>
                  slug: <code>{lab.slug}</code>
                </p>
                <p style={{ margin: "0 0 12px", fontSize: 13 }}>
                  resume: {lab.capabilities.supports_resume ? "yes" : "no"} | uploads:{" "}
                  {lab.capabilities.supports_uploads ? "yes" : "no"}
                </p>
                <button
                  type="button"
                  onClick={() => void launchLab(lab.id)}
                  disabled={creatingLabId !== null}
                >
                  {isCreatingThisLab ? "Creating session..." : "Launch lab"}
                </button>
              </article>
            );
          })}
        </div>
      )}

      {createError && (
        <p style={{ margin: "12px 0 0", color: "#9f1239" }}>Session launch error: {createError}</p>
      )}
    </section>
  );
}

export default function LabsPage() {
  const bootstrap = useShellBootstrap();
  const navigate = useNavigate();

  return (
    <LabCatalog
      apiBaseUrl={bootstrap.apiBaseUrl}
      learnerLabel={bootstrap.learnerLabel}
      onOpenSession={(sessionId) => {
        navigate(`/sessions/${sessionId}`);
      }}
    />
  );
}
