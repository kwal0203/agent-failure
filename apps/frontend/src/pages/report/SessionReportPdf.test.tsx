import { describe, expect, it } from "vitest";
import { renderSessionReportPdf } from "./renderSessionReportPdf";

describe("renderSessionReportPdf", () => {
  it("renders report sections and evidence as a PDF blob", async () => {
    const blob = await renderSessionReportPdf({
      sessionId: "test-session",
      exportedAt: new Date("2026-07-23T12:00:00.000Z"),
      sections: [
        {
          heading: "Executive Summary",
          content: "The agent disclosed a secret.\nA second paragraph.",
        },
        {
          heading: "Mitigations",
          content: "",
        },
      ],
      evidenceSections: [
        {
          heading: "Evidence & Results",
          evidence: [{ id: "event-1", title: "Token disclosed" }],
        },
        {
          heading: "Unassigned",
          evidence: [],
        },
      ],
    });

    expect(blob.type).toBe("application/pdf");
    expect(blob.size).toBeGreaterThan(0);

    const signature = new TextDecoder().decode(
      (await blob.arrayBuffer()).slice(0, 5),
    );
    expect(signature).toBe("%PDF-");
  });
});
