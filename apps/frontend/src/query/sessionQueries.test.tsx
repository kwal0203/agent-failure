import { QueryClientProvider, useQuery } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { createQueryClient } from "./queryClient";
import { latestSessionQueryOptions } from "./sessionQueries";

const getLatestSessionIdForLabMock = vi.fn();

vi.mock("../pages/labCatalogApi", () => ({
  getLatestSessionIdForLab: (...args: unknown[]) =>
    getLatestSessionIdForLabMock(...args),
}));

function LatestSessionConsumer({ label }: { label: string }) {
  const query = useQuery(
    latestSessionQueryOptions(
      "http://localhost:8000",
      "44444444-4444-4444-4444-444444444444",
    ),
  );
  return <p>{query.data ? `${label}: ${query.data}` : "Loading"}</p>;
}

describe("latestSessionQueryOptions", () => {
  it("shares one latest-session request between consumers", async () => {
    getLatestSessionIdForLabMock.mockResolvedValue(
      "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    );
    const queryClient = createQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <LatestSessionConsumer label="First" />
        <LatestSessionConsumer label="Second" />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByText("First: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Second: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    ).toBeInTheDocument();
    expect(getLatestSessionIdForLabMock).toHaveBeenCalledTimes(1);
  });
});
