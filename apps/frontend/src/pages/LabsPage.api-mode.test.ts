import { afterEach, describe, expect, it, vi } from "vitest";

describe("loadLabCatalog API mode", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("returns labs from /api/v1/labs when VITE_LAB_CATALOG_SOURCE=api", async () => {
    vi.stubEnv("VITE_LAB_CATALOG_SOURCE", "api");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        labs: [
          {
            id: "11111111-1111-1111-1111-111111111111",
            slug: "prompt-injection",
            name: "Prompt Injection",
            summary: "Practice prompt injection.",
            capabilities: {
              supports_resume: false,
              supports_uploads: false,
            },
          },
        ],
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const { loadLabCatalog } = await import("./LabsPage");
    const labs = await loadLabCatalog("http://localhost:8000");

    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/v1/labs", {
      method: "GET",
      headers: {
        Authorization: "Bearer local:kane:learner",
        "Content-Type": "application/json",
      },
    });
    expect(labs).toHaveLength(1);
    expect(labs[0]?.id).toBe("11111111-1111-1111-1111-111111111111");
  });

  it("returns explicit empty list when API responds with empty labs[]", async () => {
    vi.stubEnv("VITE_LAB_CATALOG_SOURCE", "api");
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ labs: [] }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const { loadLabCatalog } = await import("./LabsPage");
    const labs = await loadLabCatalog("http://localhost:8000");

    expect(labs).toEqual([]);
  });
});
