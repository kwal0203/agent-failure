import { pdf } from "@react-pdf/renderer";
import {
  type SessionReportPdfData,
  SessionReportPdfDocument,
} from "./SessionReportPdf";

export async function renderSessionReportPdf(
  report: SessionReportPdfData,
): Promise<Blob> {
  return pdf(<SessionReportPdfDocument report={report} />).toBlob();
}
