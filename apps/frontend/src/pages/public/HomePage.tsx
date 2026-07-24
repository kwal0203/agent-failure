import type { CSSProperties } from "react";
import { Link } from "react-router";

const sectionCardStyle: CSSProperties = {
  border: "1px solid #1c3f5b",
  borderRadius: 14,
  background: "rgba(7, 26, 43, 0.78)",
  padding: 18,
};

const featuredLabs = [
  {
    name: "Prompt Injection: Poisoned Inbox",
    status: "Available",
    summary:
      "Use the email attack console to seed malicious instructions and test agent trust boundaries.",
  },
  {
    name: "Tool Misuse",
    status: "Coming Soon",
    summary:
      "Practice abuse patterns where tool output and policy checks diverge under pressure.",
  },
] as const;

export default function HomePage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        padding: "24px",
        color: "#d7f5ff",
        background:
          "radial-gradient(1000px 600px at 10% -5%, rgba(0, 230, 255, 0.18), transparent 50%), radial-gradient(900px 540px at 95% -6%, rgba(28, 160, 255, 0.2), transparent 52%), linear-gradient(180deg, #040b14 0%, #071321 52%, #081726 100%)",
        fontFamily:
          '"Space Grotesk", "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif',
      }}
    >
      <div style={{ width: "100%", maxWidth: 1120, margin: "0 auto" }}>
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            marginBottom: 18,
          }}
        >
          <p style={{ margin: 0, color: "#86c8de", letterSpacing: 0.4 }}>
            Agent Failure Platform
          </p>
          <div style={{ display: "flex", gap: 10 }}>
            <Link
              to="/login"
              style={{
                textDecoration: "none",
                padding: "8px 12px",
                borderRadius: 10,
                border: "1px solid #285272",
                background: "#0a2236",
                color: "#bfefff",
                fontWeight: 700,
              }}
            >
              Log In
            </Link>
            <Link
              to="/signup"
              style={{
                textDecoration: "none",
                padding: "8px 12px",
                borderRadius: 10,
                border: "1px solid #2b6f98",
                background: "#0f3b5d",
                color: "#dcf9ff",
                fontWeight: 700,
              }}
            >
              Sign Up
            </Link>
          </div>
        </header>

        <section
          style={{
            border: "1px solid #1d3850",
            borderRadius: 16,
            background: "rgba(6, 20, 34, 0.75)",
            backdropFilter: "blur(6px)",
            padding: 28,
            marginBottom: 14,
          }}
        >
          <h1 style={{ margin: "0 0 12px", fontSize: 42, color: "#e8fbff" }}>
            Learn AI Agent Security Through Hands-On Labs
          </h1>
          <p style={{ margin: "0 0 22px", maxWidth: 780, lineHeight: 1.5 }}>
            Practice real adversarial patterns in an educational cyberrange:
            prompt injection, tool misuse, and evaluator-backed feedback loops.
          </p>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <Link
              to="/signup"
              style={{
                textDecoration: "none",
                padding: "10px 14px",
                borderRadius: 10,
                border: "1px solid #2b6f98",
                background: "#0f3b5d",
                color: "#dcf9ff",
                fontWeight: 700,
              }}
            >
              Get Started
            </Link>
          </div>
        </section>

        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: 12,
            marginBottom: 12,
          }}
        >
          <article style={sectionCardStyle}>
            <h2 style={{ margin: "0 0 8px", fontSize: 18 }}>How It Works</h2>
            <p style={{ margin: "0 0 6px", opacity: 0.92 }}>
              1. Launch a lab session from the app.
            </p>
            <p style={{ margin: "0 0 6px", opacity: 0.92 }}>
              2. Execute attack steps against the target workflow.
            </p>
            <p style={{ margin: 0, opacity: 0.92 }}>
              3. Analyze timeline events and learner feedback.
            </p>
          </article>

          <article style={sectionCardStyle}>
            <h2 style={{ margin: "0 0 8px", fontSize: 18 }}>Built For</h2>
            <p style={{ margin: "0 0 6px", opacity: 0.92 }}>
              Security engineers validating agent safety assumptions.
            </p>
            <p style={{ margin: "0 0 6px", opacity: 0.92 }}>
              Builders learning concrete failure and defense patterns.
            </p>
            <p style={{ margin: 0, opacity: 0.92 }}>
              Instructors running reproducible cyberrange exercises.
            </p>
          </article>

          <article style={sectionCardStyle}>
            <h2 style={{ margin: "0 0 8px", fontSize: 18 }}>Safety Scope</h2>
            <p style={{ margin: "0 0 6px", opacity: 0.92 }}>
              Educational sandbox environments only.
            </p>
            <p style={{ margin: "0 0 6px", opacity: 0.92 }}>
              Isolated runtime sessions with explicit observability.
            </p>
            <p style={{ margin: 0, opacity: 0.92 }}>
              Designed for training and controlled research workflows.
            </p>
          </article>
        </section>

        <section
          style={{
            ...sectionCardStyle,
            padding: 20,
          }}
        >
          <h2 style={{ margin: "0 0 10px", fontSize: 20 }}>Featured Labs</h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: 10,
            }}
          >
            {featuredLabs.map((lab) => (
              <article
                key={lab.name}
                style={{
                  border: "1px solid #295374",
                  borderRadius: 10,
                  padding: 12,
                  background: "rgba(9, 31, 48, 0.74)",
                }}
              >
                <div
                  style={{
                    display: "inline-flex",
                    padding: "2px 8px",
                    borderRadius: 999,
                    fontSize: 12,
                    border: "1px solid #33688d",
                    marginBottom: 8,
                    color: lab.status === "Available" ? "#7fffd8" : "#a7cce2",
                  }}
                >
                  {lab.status}
                </div>
                <h3 style={{ margin: "0 0 6px", fontSize: 16 }}>{lab.name}</h3>
                <p style={{ margin: 0, opacity: 0.92 }}>{lab.summary}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
