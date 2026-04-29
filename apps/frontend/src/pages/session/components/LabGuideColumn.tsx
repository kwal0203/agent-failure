import { getLabGuideContent } from "../labGuideContent";
import { DEMO_H2_STYLE } from "../ui";

type LabGuideColumnProps = {
  labId?: string | null;
};

export function LabGuideColumn({ labId }: LabGuideColumnProps) {
  const content = getLabGuideContent(labId);
  const missionSections = content.mission
    .split(/\n{2,}/)
    .map((section) => section.trim())
    .filter((section) => section.length > 0);

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
        className="lab-guide-scroll-region"
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
          {missionSections.map((section) => {
            const lines = section.split("\n");
            const heading = lines[0]?.trim();
            const body = lines.slice(1).join("\n").trim();
            const hasSectionHeading =
              heading === "Background" ||
              heading === "The Objective" ||
              heading === "Mission Overview";

            if (!hasSectionHeading || body.length === 0) {
              return (
                <p
                  key={section}
                  style={{ margin: "0 0 12px 0", whiteSpace: "pre-line" }}
                >
                  {section}
                </p>
              );
            }

            return (
              <div key={heading} style={{ marginBottom: 16 }}>
                <h3 style={{ margin: "0 0 8px" }}>{heading}</h3>
                {(() => {
                  const bodyLines = body.split("\n");
                  const bulletItems = bodyLines
                    .map((line) => line.trim())
                    .filter((line) => line.startsWith("- "))
                    .map((line) => line.slice(2).trim())
                    .filter((line) => line.length > 0);
                  const prose = bodyLines
                    .filter((line) => !line.trim().startsWith("- "))
                    .join("\n")
                    .trim();

                  return (
                    <>
                      {prose.length > 0 ? (
                        <p style={{ margin: 0, whiteSpace: "pre-line" }}>
                          {prose}
                        </p>
                      ) : null}
                      {bulletItems.length > 0 ? (
                        <ul
                          style={{
                            margin: prose.length > 0 ? "8px 0 0 0" : 0,
                            paddingLeft: 20,
                          }}
                        >
                          {bulletItems.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      ) : null}
                    </>
                  );
                })()}
              </div>
            );
          })}
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

      <style>{`
        .lab-guide-scroll-region {
          scrollbar-width: thin;
          scrollbar-color: #88a2b8 transparent;
        }
        .lab-guide-scroll-region::-webkit-scrollbar {
          width: 10px;
        }
        .lab-guide-scroll-region::-webkit-scrollbar-track {
          background: transparent;
        }
        .lab-guide-scroll-region::-webkit-scrollbar-thumb {
          background-color: #88a2b8;
          border-radius: 999px;
          border: 2px solid transparent;
          background-clip: content-box;
        }
        .lab-guide-scroll-region::-webkit-scrollbar-thumb:hover {
          background-color: #6f8ea8;
        }
      `}</style>
    </div>
  );
}
