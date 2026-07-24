import type {
  EditableReportSections,
  ReportSectionAssignment,
} from "../../query/sessionReportDraft";
import { createReportDraftSnapshot } from "../../query/sessionReportDraft";
import type {
  PutSessionReportDraftRequest,
  TimelineEvent,
} from "../session/types";

export const REPORT_SECTION_OPTIONS: ReadonlyArray<{
  value: ReportSectionAssignment;
  label: string;
}> = [
  { value: "unassigned", label: "Unassigned" },
  { value: "executive_summary", label: "Executive Summary" },
  { value: "threat_model", label: "Threat Model" },
  { value: "methodology", label: "Methodology" },
  { value: "evidence_and_results", label: "Evidence & Results" },
  { value: "mitigations", label: "Mitigations" },
];

export type EvidenceBySection = Map<ReportSectionAssignment, TimelineEvent[]>;

export type PendingReportSave = {
  request: PutSessionReportDraftRequest;
  snapshot: string;
};

export function toTraceEventId(timelineEventId: string): string | null {
  if (!timelineEventId.startsWith("trace-")) return null;
  const raw = timelineEventId.slice("trace-".length).trim();
  return raw.length > 0 ? raw : null;
}

export function eventTone(event: TimelineEvent): {
  chipClass: string;
  titleClass: string;
} {
  const haystack =
    `${event.title} ${event.description} ${event.details ?? ""}`.toLowerCase();
  if (
    haystack.includes("token exposed") ||
    haystack.includes("system_token") ||
    haystack.includes("orch-7429")
  ) {
    return {
      chipClass: "border border-red-500 bg-red-950/35",
      titleClass: "text-red-100",
    };
  }

  if (event.title.toLowerCase() === "malicious email received") {
    return {
      chipClass: "border border-orange-500 bg-orange-950/35",
      titleClass: "text-orange-100",
    };
  }

  if (event.title.toLowerCase() === "benign email received") {
    return {
      chipClass: "border border-emerald-500 bg-emerald-950/35",
      titleClass: "text-emerald-100",
    };
  }

  switch (event.type) {
    case "important":
      return {
        chipClass: "border border-amber-500 bg-amber-950/30",
        titleClass: "text-amber-100",
      };
    case "attacker_action":
      return {
        chipClass: "border border-violet-500 bg-violet-950/30",
        titleClass: "text-violet-100",
      };
    case "agent_action":
      return {
        chipClass: "border border-emerald-500 bg-emerald-950/30",
        titleClass: "text-emerald-100",
      };
    case "tool_call":
      return {
        chipClass: "border border-sky-500 bg-sky-950/30",
        titleClass: "text-sky-100",
      };
    case "system":
      return {
        chipClass: "border border-slate-500 bg-slate-800/45",
        titleClass: "text-slate-100",
      };
    case "explanation":
      return {
        chipClass: "border border-blue-500 bg-blue-950/30",
        titleClass: "text-blue-100",
      };
    default:
      return {
        chipClass: "border border-slate-400 bg-slate-900/25",
        titleClass: "text-slate-100",
      };
  }
}

export function groupSelectedEvidence(
  orderedEvidence: TimelineEvent[],
  selectedEventIds: Set<string>,
  selectedEventSections: Record<string, ReportSectionAssignment>,
): EvidenceBySection {
  const grouped: EvidenceBySection = new Map();
  for (const option of REPORT_SECTION_OPTIONS) {
    grouped.set(option.value, []);
  }
  for (const event of orderedEvidence) {
    if (!selectedEventIds.has(event.id)) continue;
    grouped.get(selectedEventSections[event.id] ?? "unassigned")?.push(event);
  }
  return grouped;
}

export function buildReportSave(
  draft: EditableReportSections,
  orderedEvidence: TimelineEvent[],
  selectedEventIds: Set<string>,
  selectedEventSections: Record<string, ReportSectionAssignment>,
): PendingReportSave {
  const items = orderedEvidence
    .filter(
      (event) =>
        event.report_selectable === true && selectedEventIds.has(event.id),
    )
    .map((event, index) => {
      const eventId = toTraceEventId(event.id);
      if (!eventId) return null;
      return {
        event_id: eventId,
        position: index,
        title: event.title,
        description: event.description,
        details: null,
        occurred_at: event.timestamp,
        trace_version: 1,
        event_index: index,
        evidence_type: event.evidence_type ?? "noise",
        objective_keys: event.objective_keys ?? [],
        why_it_matters: event.why_it_matters ?? null,
        default_priority: event.default_priority ?? "low",
        citation_label: null,
        objective_mapping: null,
        evidence_strength: null,
        student_note: null,
        report_section: selectedEventSections[event.id] ?? "unassigned",
        section_position: null,
      };
    })
    .filter((item) => item !== null);
  const selectedEvidenceIds = items.map((item) => item.event_id);
  const evidenceSectionsById = Object.fromEntries(
    items.map((item) => [
      item.event_id,
      item.report_section as ReportSectionAssignment,
    ]),
  );

  return {
    snapshot: createReportDraftSnapshot({
      sections: draft,
      selectedEvidenceIds,
      evidenceSectionsById,
    }),
    request: {
      sections: {
        executive_summary: draft.executiveSummary,
        threat_model: draft.threatModel,
        methodology: draft.methodology,
        evidence_and_results: draft.evidenceAndResults,
        mitigations: draft.mitigations,
      },
      items,
    },
  };
}
