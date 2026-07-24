import { useMemo, useState } from "react";
import type {
  EditableReportSections,
  PersistedReportDraft,
  ReportSectionAssignment,
} from "../../query/sessionReportDraft";
import type { TimelineEvent } from "../session/types";
import {
  buildReportSave,
  groupSelectedEvidence,
  toTraceEventId,
} from "./reportModel";

type ReportEditorState = {
  draft: EditableReportSections;
  hydratedSnapshot: string;
  selectedEventIds: Set<string>;
  selectedEventSections: Record<string, ReportSectionAssignment>;
};

function hydrateEditorState(
  orderedEvidence: TimelineEvent[],
  persistedDraft: PersistedReportDraft,
): ReportEditorState {
  const selectedEventIds = new Set<string>();
  const selectedEventSections: Record<string, ReportSectionAssignment> = {};
  const persistedEvidenceIds = new Set(persistedDraft.selectedEvidenceIds);

  for (const event of orderedEvidence) {
    if (event.report_selectable !== true) continue;
    const traceEventId = toTraceEventId(event.id);
    if (!traceEventId || !persistedEvidenceIds.has(traceEventId)) continue;
    selectedEventIds.add(event.id);
    selectedEventSections[event.id] =
      persistedDraft.evidenceSectionsById[traceEventId] ?? "unassigned";
  }

  return {
    draft: persistedDraft.sections,
    hydratedSnapshot: persistedDraft.persistedSnapshot,
    selectedEventIds,
    selectedEventSections,
  };
}

export function useReportEditor({
  orderedEvidence,
  persistedDraft,
}: {
  orderedEvidence: TimelineEvent[];
  persistedDraft: PersistedReportDraft;
}) {
  const [state, setState] = useState(() =>
    hydrateEditorState(orderedEvidence, persistedDraft),
  );
  const selectedEvidenceBySection = useMemo(
    () =>
      groupSelectedEvidence(
        orderedEvidence,
        state.selectedEventIds,
        state.selectedEventSections,
      ),
    [orderedEvidence, state.selectedEventIds, state.selectedEventSections],
  );
  const currentSave = useMemo(
    () =>
      buildReportSave(
        state.draft,
        orderedEvidence,
        state.selectedEventIds,
        state.selectedEventSections,
      ),
    [
      orderedEvidence,
      state.draft,
      state.selectedEventIds,
      state.selectedEventSections,
    ],
  );

  const selectEvent = (eventId: string) => {
    setState((previous) => ({
      ...previous,
      selectedEventIds: new Set(previous.selectedEventIds).add(eventId),
      selectedEventSections: previous.selectedEventSections[eventId]
        ? previous.selectedEventSections
        : { ...previous.selectedEventSections, [eventId]: "unassigned" },
    }));
  };

  const removeEventSelection = (eventId: string) => {
    setState((previous) => {
      const selectedEventIds = new Set(previous.selectedEventIds);
      selectedEventIds.delete(eventId);
      return { ...previous, selectedEventIds };
    });
  };

  const setEventSection = (
    eventId: string,
    section: ReportSectionAssignment,
  ) => {
    setState((previous) => ({
      ...previous,
      selectedEventSections: {
        ...previous.selectedEventSections,
        [eventId]: section,
      },
    }));
  };

  const updateDraftField = <K extends keyof EditableReportSections>(
    key: K,
    value: EditableReportSections[K],
  ) => {
    setState((previous) => ({
      ...previous,
      draft: { ...previous.draft, [key]: value },
    }));
  };

  return {
    currentSave,
    draft: state.draft,
    hydratedSnapshot: state.hydratedSnapshot,
    removeEventSelection,
    selectEvent,
    selectedEvidenceBySection,
    selectedEventIds: state.selectedEventIds,
    selectedEventSections: state.selectedEventSections,
    setEventSection,
    updateDraftField,
  };
}
