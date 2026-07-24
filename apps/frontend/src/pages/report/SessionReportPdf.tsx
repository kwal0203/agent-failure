import { Document, Page, StyleSheet, Text, View } from "@react-pdf/renderer";

export type SessionReportPdfData = {
  sessionId: string;
  exportedAt: Date;
  sections: ReadonlyArray<{
    heading: string;
    content: string;
  }>;
  evidenceSections: ReadonlyArray<{
    heading: string;
    evidence: ReadonlyArray<{
      id: string;
      title: string;
    }>;
  }>;
};

const styles = StyleSheet.create({
  page: {
    paddingTop: 54,
    paddingRight: 48,
    paddingBottom: 54,
    paddingLeft: 48,
    fontFamily: "Helvetica",
    fontSize: 10,
    lineHeight: 1.5,
    color: "#172033",
  },
  header: {
    marginBottom: 24,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#84cc16",
  },
  title: {
    marginBottom: 5,
    fontFamily: "Helvetica-Bold",
    fontSize: 20,
    color: "#18230f",
  },
  metadata: {
    fontSize: 9,
    color: "#52606d",
  },
  section: {
    marginBottom: 18,
  },
  sectionHeading: {
    marginBottom: 6,
    fontFamily: "Helvetica-Bold",
    fontSize: 13,
    color: "#365314",
  },
  paragraph: {
    marginBottom: 5,
  },
  emptyText: {
    color: "#64748b",
    fontStyle: "italic",
  },
  evidenceHeading: {
    marginTop: 4,
    marginBottom: 10,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: "#cbd5e1",
    fontFamily: "Helvetica-Bold",
    fontSize: 15,
    color: "#18230f",
  },
  evidenceGroup: {
    marginBottom: 10,
  },
  evidenceGroupHeading: {
    marginBottom: 3,
    fontFamily: "Helvetica-Bold",
    fontSize: 11,
  },
  evidenceItem: {
    marginBottom: 2,
    paddingLeft: 10,
  },
  footer: {
    position: "absolute",
    right: 48,
    bottom: 24,
    left: 48,
    fontSize: 8,
    textAlign: "center",
    color: "#64748b",
  },
});

function SectionBody({ content }: { content: string }) {
  const paragraphs = content
    .split("\n")
    .map((paragraph) => paragraph.trim())
    .filter((paragraph) => paragraph.length > 0);

  if (paragraphs.length === 0) {
    return <Text style={styles.emptyText}>Not provided.</Text>;
  }

  return <Text style={styles.paragraph}>{paragraphs.join("\n\n")}</Text>;
}

export function SessionReportPdfDocument({
  report,
}: {
  report: SessionReportPdfData;
}) {
  return (
    <Document
      title="Agent Failure Lab Report"
      subject={`Lab report for session ${report.sessionId}`}
      creator="Agent Failure"
      creationDate={report.exportedAt}
    >
      <Page size="LETTER" style={styles.page} wrap>
        <View style={styles.header}>
          <Text style={styles.title}>Agent Failure Lab Report</Text>
          <Text style={styles.metadata}>Session: {report.sessionId}</Text>
          <Text style={styles.metadata}>
            Exported: {report.exportedAt.toISOString()}
          </Text>
        </View>

        {report.sections.map((section) => (
          <View key={section.heading} style={styles.section}>
            <Text style={styles.sectionHeading} minPresenceAhead={24}>
              {section.heading}
            </Text>
            <SectionBody content={section.content} />
          </View>
        ))}

        <Text style={styles.evidenceHeading} minPresenceAhead={24}>
          Evidence By Section
        </Text>
        {report.evidenceSections.map((section) => (
          <View key={section.heading} style={styles.evidenceGroup}>
            <Text style={styles.evidenceGroupHeading} minPresenceAhead={16}>
              {section.heading}
            </Text>
            {section.evidence.length === 0 ? (
              <Text style={styles.emptyText}>None</Text>
            ) : (
              section.evidence.map((evidence) => (
                <Text key={evidence.id} style={styles.evidenceItem}>
                  {`• ${evidence.title} (evidence)`}
                </Text>
              ))
            )}
          </View>
        ))}

        <Text
          style={styles.footer}
          fixed
          render={({ pageNumber, totalPages }) =>
            `Agent Failure · ${pageNumber} / ${totalPages}`
          }
        />
      </Page>
    </Document>
  );
}
