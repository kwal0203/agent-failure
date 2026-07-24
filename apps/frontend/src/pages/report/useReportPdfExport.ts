import { useCallback, useEffect, useRef, useState } from "react";
import type { EditableReportSections } from "../../query/sessionReportDraft";
import type { EvidenceBySection } from "./reportModel";
import { REPORT_SECTION_OPTIONS } from "./reportModel";

export function useReportPdfExport({
  draft,
  evidenceBySection,
  flushSave,
  sessionId,
}: {
  draft: EditableReportSections;
  evidenceBySection: EvidenceBySection;
  flushSave: () => Promise<boolean>;
  sessionId?: string;
}) {
  const [error, setError] = useState<string | null>(null);
  const [isExporting, setIsExporting] = useState(false);
  const latestDraftRef = useRef(draft);
  const latestEvidenceBySectionRef = useRef(evidenceBySection);

  useEffect(() => {
    latestDraftRef.current = draft;
    latestEvidenceBySectionRef.current = evidenceBySection;
  }, [draft, evidenceBySection]);

  const exportReport = useCallback(async () => {
    setIsExporting(true);
    setError(null);
    try {
      if (!(await flushSave())) return;
      const exportDraft = latestDraftRef.current;
      const exportEvidenceBySection = latestEvidenceBySectionRef.current;
      const { renderSessionReportPdf } = await import(
        "./renderSessionReportPdf"
      );
      const pdfBlob = await renderSessionReportPdf({
        sessionId: sessionId ?? "unknown",
        exportedAt: new Date(),
        sections: [
          {
            heading: "Executive Summary",
            content: exportDraft.executiveSummary,
          },
          { heading: "Threat Model", content: exportDraft.threatModel },
          {
            heading: "Exploitation Methodology",
            content: exportDraft.methodology,
          },
          {
            heading: "Evidence and Results",
            content: exportDraft.evidenceAndResults,
          },
          { heading: "Mitigations", content: exportDraft.mitigations },
        ],
        evidenceSections: REPORT_SECTION_OPTIONS.map((section) => ({
          heading: section.label,
          evidence: (exportEvidenceBySection.get(section.value) ?? []).map(
            (event) => ({ id: event.id, title: event.title }),
          ),
        })),
      });
      const url = URL.createObjectURL(pdfBlob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `session-report-${sessionId ?? "unknown"}-${new Date()
        .toISOString()
        .slice(0, 10)}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (exportError) {
      setError(
        exportError instanceof Error
          ? `Failed to export report: ${exportError.message}`
          : "Failed to export report",
      );
    } finally {
      setIsExporting(false);
    }
  }, [flushSave, sessionId]);

  return { error, exportReport, isExporting };
}
