import { afterEach, describe, expect, it, vi } from "vitest";

describe("loadLabCatalog API mode", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("returns labs from /api/v1/labs when VITE_LAB_CATALOG_SOURCE=api", async () => {
    vi.stubEnv("VITE_LAB_CATALOG_SOURCE", "api");
    vi.doMock("../auth/session", () => ({
      getCurrentAuthHeader: async () => "Bearer test-token",
    }));
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        labs: [
          {
            id: "55555555-5555-5555-5555-555555555555",
            slug: "agent-tool-misuse",
            name: "Tool Misuse",
            summary: "Induce unsafe tool operations via deceptive inputs.",
            capabilities: {
              supports_resume: false,
              supports_uploads: false,
            },
          },
        ],
      }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const { loadLabCatalog } = await import("./labCatalogApi");
    const labs = await loadLabCatalog("http://localhost:8000");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/labs",
      {
        method: "GET",
        headers: {
          Authorization: "Bearer test-token",
          "Content-Type": "application/json",
        },
      },
    );
    expect(labs).toHaveLength(1);
    expect(labs[0]?.id).toBe("55555555-5555-5555-5555-555555555555");
  });

  it("returns explicit empty list when API responds with empty labs[]", async () => {
    vi.stubEnv("VITE_LAB_CATALOG_SOURCE", "api");
    vi.doMock("../auth/session", () => ({
      getCurrentAuthHeader: async () => "Bearer test-token",
    }));
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => ({ labs: [] }),
    }));
    vi.stubGlobal("fetch", fetchMock);

    const { loadLabCatalog } = await import("./labCatalogApi");
    const labs = await loadLabCatalog("http://localhost:8000");

    expect(labs).toEqual([]);
  });
});
