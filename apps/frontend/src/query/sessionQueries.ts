import { queryOptions } from "@tanstack/react-query";
import { getLatestSessionIdForLab } from "../pages/labCatalogApi";

export const sessionQueryKeys = {
  all: ["sessions"] as const,
  latestForLab: (apiBaseUrl: string, labId: string) =>
    [...sessionQueryKeys.all, "latest", apiBaseUrl, labId] as const,
};

export function latestSessionQueryOptions(apiBaseUrl: string, labId: string) {
  return queryOptions({
    queryKey: sessionQueryKeys.latestForLab(apiBaseUrl, labId),
    queryFn: () => getLatestSessionIdForLab(apiBaseUrl, labId),
  });
}
