import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useShellBootstrap } from "../shell/context";
import {
  createSessionForLab,
  type LabCatalogItem,
  type LabDifficulty,
  loadLabCatalog,
} from "./labCatalogApi";

type PreLabRouteState = {
  labId?: string;
  labName?: string;
  labSlug?: string;
  labSummary?: string;
  labDifficulty?: LabDifficulty;
};

type BriefingContent = {
  title: string;
  oneLiner: string;
  estimatedTime: string;
  topic: string;
  missionOverview: string;
  scenario: string;
  systemContext: string;
  rules: string[];
  learningGoals: string[];
  objective: string;
  target: string;
  attackVector: string;
  successCriteria: string[];
  evidence: string[];
};

const DEFAULT_BRIEFING: BriefingContent = {
  title: "Lab Mission Briefing",
  oneLiner:
    "Review the mission context, objective, and rules before entering the lab runtime.",
  estimatedTime: "15-25 min",
  topic: "AI Agent Security",
  missionOverview:
    "You are acting as a security assessor evaluating a vulnerable AI agent workflow.",
  scenario:
    "The lab simulates a realistic agent environment where untrusted inputs can influence model behavior.",
  systemContext:
    "You will use the provided interface to interact with the agent and collect evidence from visible system events.",
  rules: [
    "Use only the provided lab interface and tools.",
    "Do not attempt backend access or out-of-band data collection.",
    "Keep activity within this controlled educational environment.",
  ],
  learningGoals: [
    "Identify trust-boundary weaknesses in agent workflows.",
    "Demonstrate an exploit path with trace evidence.",
    "Explain root cause and propose practical mitigations.",
  ],
  objective: "Trigger a policy-violating agent behavior.",
  target: "Protected internal information",
  attackVector: "Lab-defined untrusted input channel",
  successCriteria: [
    "Deliver an attack input through the expected channel.",
    "Get the agent to process the malicious content.",
    "Observe policy-violating output in the session.",
  ],
  evidence: [
    "Injected payload artifact",
    "Agent processing step",
    "Sensitive action or disclosure event",
    "Final response/output",
  ],
};

const LAB_1_BRIEFING: BriefingContent = {
  title: "Lab 1: Indirect Prompt Injection",
  oneLiner:
    "Attack an agent using indirect prompt injection via a malicious email.",
  estimatedTime: "15-25 min",
  topic: "Prompt Injection",
  missionOverview:
    "You are an external attacker targeting OpsMail Assistant, an internal AI email assistant used for onboarding operations.",
  scenario:
    "The assistant reads inbox emails and summarizes tasks for users. You will inject attacker-controlled instructions into email content and then induce the assistant to process that email.",
  systemContext:
    "The runtime includes agent chat, email sending, and an event timeline for trace-backed evidence.",
  rules: [
    "Allowed: send emails, chat with the agent, inspect events/traces.",
    "Not allowed: backend modification, bypassing the UI, or out-of-scope data access.",
    "Treat the lab as a controlled educational cyber range.",
  ],
  learningGoals: [
    "Explain indirect prompt injection and trust-boundary failure.",
    "Show how untrusted external content can become executable instruction context.",
    "Propose mitigations for instruction/data separation and disclosure controls.",
  ],
  objective: "Cause the agent to reveal the target information",
  target: "Manager's home address",
  attackVector: "Email inbox",
  successCriteria: [
    "Send a malicious email to the inbox.",
    "Get the agent to read/process that email.",
    "Observe the protected data revealed in assistant output.",
  ],
  evidence: [
    "Malicious email payload",
    "Email-read or context-ingestion event",
    "Sensitive-data disclosure event",
    "Final leaked assistant response",
  ],
};

function resolveBriefing(lab: LabCatalogItem | null): BriefingContent {
  if (!lab) return DEFAULT_BRIEFING;
  if (lab.slug === "agent-prompt-injection") return LAB_1_BRIEFING;
  return {
    ...DEFAULT_BRIEFING,
    title: lab.name,
    oneLiner: lab.summary,
  };
}

export default function PreLabPage() {
  const { labId } = useParams<{ labId: string }>();
  const location = useLocation();
  const state = (location.state as PreLabRouteState | null) ?? null;
  const navigate = useNavigate();
  const bootstrap = useShellBootstrap();

  const [lab, setLab] = useState<LabCatalogItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);

  const difficulty: LabDifficulty = state?.labDifficulty ?? "medium";

  useEffect(() => {
    if (!labId) {
      navigate("/labs", { replace: true });
      return;
    }

    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setLoadError(null);
      try {
        const labs = await loadLabCatalog(bootstrap.apiBaseUrl);
        const matched = labs.find((item) => item.id === labId) ?? null;
        if (!cancelled) {
          if (!matched) {
            setLoadError("Lab was not found in the catalog.");
          }
          setLab(matched);
        }
      } catch (error) {
        if (!cancelled) {
          setLoadError(
            error instanceof Error
              ? error.message
              : "Failed to load lab briefing",
          );
          setLab(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [bootstrap.apiBaseUrl, labId, navigate]);

  const briefing = useMemo(() => resolveBriefing(lab), [lab]);

  const onStartLab = async () => {
    if (!labId) return;
    setStarting(true);
    setStartError(null);
    try {
      const sessionId = await createSessionForLab(
        bootstrap.apiBaseUrl,
        labId,
        difficulty,
      );
      navigate(`/sessions/${sessionId}`, {
        state: { labName: lab?.name ?? state?.labName ?? "Lab Session" },
      });
    } catch (error) {
      setStartError(
        error instanceof Error ? error.message : "Session create failed",
      );
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return <p style={{ margin: 0 }}>Loading pre-lab briefing...</p>;
  }

  if (loadError) {
    return (
      <section>
        <h1 style={{ marginTop: 0 }}>Pre-Lab Briefing</h1>
        <p style={{ color: "#fca5a5" }}>Error: {loadError}</p>
        <button type="button" onClick={() => navigate("/labs")}>
          Back to Labs
        </button>
      </section>
    );
  }

  const labName = state?.labName ?? lab?.name ?? briefing.title;
  const missionOneLiner = state?.labSummary ?? briefing.oneLiner;

  return (
    <section
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 16,
        color: "#d8f7ff",
      }}
    >
      <header
        style={{
          border: "1px solid #1f4460",
          borderRadius: 14,
          padding: "24px 26px",
          background:
            "linear-gradient(160deg, rgba(11,27,42,0.98), rgba(8,18,31,0.95))",
        }}
      >
        <h1 style={{ margin: "14px 0 12px", color: "#f3feff" }}>{labName}</h1>
        <p style={{ margin: "0 0 14px", color: "#b4deed", lineHeight: 1.5 }}>
          {missionOneLiner}
        </p>
        <p style={{ margin: 0, color: "#87b7cc", fontSize: 13 }}>
          {difficulty} • {briefing.estimatedTime} • {briefing.topic}
        </p>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: 14,
          alignItems: "start",
        }}
      >
        <div style={{ display: "grid", gap: 10 }}>
          {[
            ["Mission Overview", briefing.missionOverview],
            ["Scenario", briefing.scenario],
            ["System Context", briefing.systemContext],
          ].map(([title, body]) => (
            <article
              key={title}
              style={{
                border: "1px solid #1f4460",
                borderRadius: 12,
                padding: 14,
                background: "rgba(8,18,31,0.95)",
              }}
            >
              <h2 style={{ margin: "0 0 6px", fontSize: 18, color: "#f3feff" }}>
                {title}
              </h2>
              <p style={{ margin: 0, color: "#a9d3e3" }}>{body}</p>
            </article>
          ))}

          <article
            style={{
              border: "1px solid #1f4460",
              borderRadius: 12,
              padding: 14,
              background: "rgba(8,18,31,0.95)",
            }}
          >
            <h2 style={{ margin: "0 0 6px", fontSize: 18, color: "#f3feff" }}>
              Learning Goals
            </h2>
            <ul style={{ margin: 0, paddingLeft: 18, color: "#a9d3e3" }}>
              {briefing.learningGoals.map((goal) => (
                <li key={goal}>{goal}</li>
              ))}
            </ul>
          </article>
        </div>

        <aside
          style={{
            position: "sticky",
            top: 84,
            border: "1px solid #1f4460",
            borderRadius: 12,
            padding: 14,
            background: "rgba(8,18,31,0.98)",
            display: "grid",
            gap: 10,
          }}
        >
          <h2 style={{ margin: 0, fontSize: 20, color: "#f3feff" }}>
            Mission Summary
          </h2>
          <p style={{ margin: 0 }}>
            <strong>Objective:</strong> {briefing.objective}
          </p>
          <p style={{ margin: 0 }}>
            <strong>Target:</strong> {briefing.target}
          </p>
          <p style={{ margin: 0 }}>
            <strong>Attack Vector:</strong> {briefing.attackVector}
          </p>

          <div>
            <p style={{ margin: "0 0 6px" }}>
              <strong>Success Criteria</strong>
            </p>
            <ul style={{ margin: 0, paddingLeft: 18, color: "#a9d3e3" }}>
              {briefing.successCriteria.map((criterion) => (
                <li key={criterion}>{criterion}</li>
              ))}
            </ul>
          </div>

          <div>
            <p style={{ margin: "0 0 6px" }}>
              <strong>Evidence to Capture</strong>
            </p>
            <ul style={{ margin: 0, paddingLeft: 18, color: "#a9d3e3" }}>
              {briefing.evidence.map((entry) => (
                <li key={entry}>{entry}</li>
              ))}
            </ul>
          </div>

          <button
            type="button"
            onClick={() => void onStartLab()}
            disabled={starting}
            style={{
              background: starting ? "#123652" : "#1a8fff",
              color: "#02101a",
              border: 0,
              padding: "10px 14px",
              borderRadius: 10,
              fontWeight: 800,
              cursor: starting ? "wait" : "pointer",
            }}
          >
            {starting ? "Starting lab..." : "Start Lab"}
          </button>

          {startError ? (
            <p style={{ margin: 0, color: "#ffc6d8" }}>{startError}</p>
          ) : null}
        </aside>
      </div>
    </section>
  );
}
