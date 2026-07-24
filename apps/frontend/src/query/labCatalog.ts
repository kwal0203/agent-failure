import { useQuery } from "@tanstack/react-query";
import { type LabCatalogItem, loadLabCatalog } from "../pages/labCatalogApi";

export const labCatalogQueryKeys = {
  all: ["labs"] as const,
  catalog: (apiBaseUrl: string) =>
    [...labCatalogQueryKeys.all, "catalog", apiBaseUrl] as const,
};

export function useLabCatalogQuery(
  apiBaseUrl: string,
  loadLabs: (apiBaseUrl: string) => Promise<LabCatalogItem[]> = loadLabCatalog,
) {
  return useQuery({
    queryKey: labCatalogQueryKeys.catalog(apiBaseUrl),
    queryFn: () => loadLabs(apiBaseUrl),
  });
}
