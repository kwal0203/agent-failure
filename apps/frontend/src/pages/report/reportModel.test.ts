import { describe, expect, it } from "vitest";
import type { EditableReportSections } from "../../query/sessionReportDraft";
import type { TimelineEvent } from "../session/types";
import {
  buildReportSave,
  groupSelectedEvidence,
  toTraceEventId,
} from "./reportModel";

const EMPTY_DRAFT: EditableReportSections = {
  executiveSummary: "",
  threatModel: "",
  methodology: "",
  evidenceAndResults: "",
  mitigations: "",
};

function evidence(overrides: Partial<TimelineEvent>): TimelineEvent {
  return {
    id: "trace-event-a",
    timestamp: "2026-05-24T00:00:00Z",
    type: "important",
    granularity: "high",
    title: "Evidence A",
    description: "Description A",
    report_selectable: true,
    ...overrides,
  };
}

describe("report evidence model", () => {
  it("extracts only persisted trace identifiers", () => {
    expect(toTraceEventId("trace-event-a")).toBe("event-a");
    expect(toTraceEventId("event-a")).toBeNull();
    expect(toTraceEventId("trace- ")).toBeNull();
  });

  it("groups selected evidence into its assigned report section", () => {
    const eventA = evidence({});
    const eventB = evidence({ id: "trace-event-b", title: "Evidence B" });

    const grouped = groupSelectedEvidence(
      [eventA, eventB],
      new Set([eventA.id]),
      { [eventA.id]: "methodology" },
    );

    expect(grouped.get("methodology")).toEqual([eventA]);
    expect(grouped.get("unassigned")).toEqual([]);
  });

  it("builds the persisted request and stable snapshot from selected evidence", () => {
    const event = evidence({
      evidence_type: "exploit_step",
      objective_keys: ["lab.objective"],
      why_it_matters: "Demonstrates the exploit",
      default_priority: "high",
    });

    const save = buildReportSave(
      { ...EMPTY_DRAFT, executiveSummary: "Summary" },
      [event],
      new Set([event.id]),
      { [event.id]: "evidence_and_results" },
    );

    expect(save.request).toMatchObject({
      sections: { executive_summary: "Summary" },
      items: [
        {
          event_id: "event-a",
          report_section: "evidence_and_results",
          evidence_type: "exploit_step",
        },
      ],
    });
    expect(JSON.parse(save.snapshot)).toMatchObject({
      selectedEvidenceIds: ["event-a"],
      evidenceSectionsById: {
        "event-a": "evidence_and_results",
      },
    });
  });
});
