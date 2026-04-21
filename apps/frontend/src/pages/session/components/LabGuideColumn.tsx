import { getLabGuideContent } from "../labGuideContent";
import { DEMO_H2_STYLE } from "../ui";

type LabGuideColumnProps = {
  labId?: string | null;
};

export function LabGuideColumn({ labId }: LabGuideColumnProps) {
  const content = getLabGuideContent(labId);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        height: "100%",
        minHeight: 0,
      }}
    >
      <section
        style={{
          border: "1px solid #ddd",
          borderRadius: 8,
          padding: 16,
          flex: "1 1 auto",
          minHeight: 0,
          overflowY: "auto",
        }}
      >
        <h2 style={DEMO_H2_STYLE}>Lab Guide</h2>
        <p style={{ margin: "8px 0 4px 0", fontWeight: 600 }}>
          {content.title}
        </p>
        <p style={{ margin: 0, fontSize: 13, opacity: 0.85 }}>
          {content.difficultyAndTime}
        </p>
        <div style={{ marginTop: 20 }}>
          <h3 style={{ margin: "0 0 8px" }}>Mission</h3>
          <p style={{ margin: 0 }}>{content.mission}</p>
        </div>
        <div style={{ marginTop: 20 }}>
          <h3 style={{ margin: "0 0 8px" }}>Scenario</h3>
          <p style={{ margin: 0 }}>{content.scenario}</p>
        </div>
        <div style={{ marginTop: 20 }}>
          <h3 style={{ margin: "0 0 8px" }}>Success Criteria</h3>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {content.successCriteria.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
