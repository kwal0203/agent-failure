import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useLabCatalogQuery } from "./labCatalog";
import { createQueryClient } from "./queryClient";

const labs = [
  {
    id: "44444444-4444-4444-4444-444444444444",
    slug: "agent-prompt-injection",
    name: "Indirect Prompt Injection",
    summary: "Summary",
    capabilities: {
      supports_resume: true,
      supports_uploads: false,
    },
  },
];

function CatalogConsumer({
  label,
  loadLabs,
}: {
  label: string;
  loadLabs: () => Promise<typeof labs>;
}) {
  const query = useLabCatalogQuery("http://localhost:8000", loadLabs);
  return <p>{query.data ? `${label}: ${query.data[0]?.name}` : "Loading"}</p>;
}

describe("useLabCatalogQuery", () => {
  it("shares one catalog request between consumers", async () => {
    const loadLabs = vi.fn(async () => labs);
    const queryClient = createQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <CatalogConsumer label="Labs" loadLabs={loadLabs} />
        <CatalogConsumer label="Reports" loadLabs={loadLabs} />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByText("Labs: Indirect Prompt Injection"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Reports: Indirect Prompt Injection"),
    ).toBeInTheDocument();
    expect(loadLabs).toHaveBeenCalledTimes(1);
  });
});
