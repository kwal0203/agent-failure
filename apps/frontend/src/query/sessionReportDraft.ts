import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  controlPlaneRequestError,
  createControlPlaneClient,
} from "../api/client";
import type {
  GetSessionReportDraftResponse,
  PutSessionReportDraftRequest,
} from "../pages/session/types";
import { API_BASE, getAuthHeader } from "../pages/session/ui";

export type EditableReportSections = {
  executiveSummary: string;
  threatModel: string;
  methodology: string;
  evidenceAndResults: string;
  mitigations: string;
};

export type ReportSectionAssignment =
  | "unassigned"
  | "executive_summary"
  | "threat_model"
  | "methodology"
  | "evidence_and_results"
  | "mitigations";

export type PersistedReportDraft = {
  sections: EditableReportSections;
  selectedEvidenceIds: string[];
  evidenceSectionsById: Record<string, ReportSectionAssignment>;
  persistedSnapshot: string;
};

const VALID_REPORT_SECTIONS = new Set<ReportSectionAssignment>([
  "unassigned",
  "executive_summary",
  "threat_model",
  "methodology",
  "evidence_and_results",
  "mitigations",
]);

export const EMPTY_REPORT_SECTIONS: EditableReportSections = {
  executiveSummary: "",
  threatModel: "",
  methodology: "",
  evidenceAndResults: "",
  mitigations: "",
};

export const sessionReportDraftQueryKey = (sessionId: string) =>
  ["sessions", sessionId, "report-draft"] as const;

export function createReportDraftSnapshot(input: {
  sections: EditableReportSections;
  selectedEvidenceIds: Iterable<string>;
  evidenceSectionsById: Record<string, ReportSectionAssignment>;
}): string {
  const selectedEvidenceIds = [...new Set(input.selectedEvidenceIds)].sort();
  const evidenceSectionsById = Object.fromEntries(
    selectedEvidenceIds.map((eventId) => [
      eventId,
      input.evidenceSectionsById[eventId] ?? "unassigned",
    ]),
  );

  return JSON.stringify({
    sections: input.sections,
    selectedEvidenceIds,
    evidenceSectionsById,
  });
}

export function normalizeSessionReportDraft(
  payload: GetSessionReportDraftResponse,
): PersistedReportDraft {
  const sections: EditableReportSections = {
    executiveSummary: payload.sections?.executive_summary ?? "",
    threatModel: payload.sections?.threat_model ?? "",
    methodology: payload.sections?.methodology ?? "",
    evidenceAndResults: payload.sections?.evidence_and_results ?? "",
    mitigations: payload.sections?.mitigations ?? "",
  };
  const selectedEvidenceIds: string[] = [];
  const evidenceSectionsById: Record<string, ReportSectionAssignment> = {};

  for (const item of Array.isArray(payload.items) ? payload.items : []) {
    const eventId = item?.event_id;
    if (!eventId || selectedEvidenceIds.includes(eventId)) {
      continue;
    }
    const reportSection = VALID_REPORT_SECTIONS.has(
      item.report_section as ReportSectionAssignment,
    )
      ? (item.report_section as ReportSectionAssignment)
      : "unassigned";
    selectedEvidenceIds.push(eventId);
    evidenceSectionsById[eventId] = reportSection;
  }

  selectedEvidenceIds.sort();
  const persistedSnapshot = createReportDraftSnapshot({
    sections,
    selectedEvidenceIds,
    evidenceSectionsById,
  });

  return {
    sections,
    selectedEvidenceIds,
    evidenceSectionsById,
    persistedSnapshot,
  };
}

export async function getSessionReportDraft(
  sessionId: string,
): Promise<PersistedReportDraft> {
  const { data, error, response } = await createControlPlaneClient(
    API_BASE,
  ).GET("/api/v1/sessions/{session_id}/report-draft", {
    params: {
      path: { session_id: sessionId },
      header: { Authorization: await getAuthHeader() },
    },
  });

  if (error || !data) {
    throw controlPlaneRequestError(
      error,
      response,
      "Failed to load report draft",
    );
  }

  return normalizeSessionReportDraft(data);
}

export async function putSessionReportDraft(
  sessionId: string,
  request: PutSessionReportDraftRequest,
): Promise<PersistedReportDraft> {
  const { data, error, response } = await createControlPlaneClient(
    API_BASE,
  ).PUT("/api/v1/sessions/{session_id}/report-draft", {
    params: {
      path: { session_id: sessionId },
      header: { Authorization: await getAuthHeader() },
    },
    body: request,
  });

  if (error || !data) {
    throw controlPlaneRequestError(
      error,
      response,
      "Failed to save report draft",
    );
  }

  return normalizeSessionReportDraft(data);
}

export function useSessionReportDraftQuery(sessionId?: string) {
  return useQuery({
    queryKey: sessionReportDraftQueryKey(sessionId ?? ""),
    queryFn: () => getSessionReportDraft(sessionId ?? ""),
    enabled: Boolean(sessionId),
  });
}

export function useSaveSessionReportDraftMutation(sessionId?: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ["sessions", sessionId ?? "", "report-draft", "save"],
    mutationFn: (request: PutSessionReportDraftRequest) => {
      if (!sessionId) {
        throw new Error("A session ID is required to save a report draft");
      }
      return putSessionReportDraft(sessionId, request);
    },
    onSuccess: (persistedDraft) => {
      if (!sessionId) return;
      queryClient.setQueryData(
        sessionReportDraftQueryKey(sessionId),
        persistedDraft,
      );
    },
  });
}
