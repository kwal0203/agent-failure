import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  type RenderOptions,
  type RenderResult,
  render,
} from "@testing-library/react";
import type { ReactNode } from "react";
import { createQueryClient } from "../query/queryClient";

export function renderWithQueryClient(
  ui: ReactNode,
  options?: Omit<RenderOptions, "wrapper">,
): RenderResult & { queryClient: QueryClient } {
  const queryClient = createQueryClient();
  queryClient.setDefaultOptions({
    queries: {
      retry: false,
    },
    mutations: {
      retry: false,
    },
  });

  const result = render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
    options,
  );
  return { ...result, queryClient };
}
