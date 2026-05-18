import {
  ArrowLeft,
  BarChart3,
  BookOpen,
  Camera,
  Check,
  CheckSquare,
  ClipboardList,
  Clock,
  Flag,
  GraduationCap,
  HelpCircle,
  Lock,
  Mail,
  MessageCircle,
  Play,
  Radar,
  Search,
  Shield,
  Tag,
  Target,
  User,
  Wifi,
} from "lucide-react";
import {
  type ElementType,
  type ReactNode,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { useShellBootstrap } from "../shell/context";
import {
  createSessionForLab,
  type LabCatalogItem,
  type LabDifficulty,
  loadLabCatalog,
} from "./labCatalogApi";

const LATEST_SESSION_BY_LAB_KEY = "agentfailure.latestSessionByLab";

function rememberLatestSessionForLab(labId: string, sessionId: string): void {
  try {
    const raw = window.localStorage.getItem(LATEST_SESSION_BY_LAB_KEY);
    const parsed: Record<string, string> = raw
      ? (JSON.parse(raw) as Record<string, string>)
      : {};
    parsed[labId] = sessionId;
    window.localStorage.setItem(
      LATEST_SESSION_BY_LAB_KEY,
      JSON.stringify(parsed),
    );
  } catch {
    // Non-fatal: reporting shortcut can still be accessed manually by URL.
  }
}

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

type BriefingSection = {
  number: number;
  title: string;
  icon: ElementType;
  content: ReactNode;
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
    "You are an external attacker testing OpsMail Assistant, an internal AI email assistant used for onboarding operations. Your goal is to determine whether attacker-controlled email content can influence the assistant's behavior and cause it to disclose protected information.",
  scenario:
    "OpsMail Assistant reads inbox emails and summarizes tasks for users. Some inbox content may come from external or untrusted sources. You will send a malicious email, then interact with the assistant as a normal user to see whether the email content is treated as data to summarize or as instructions to follow.",
  systemContext:
    "The runtime includes agent chat, email sending, and an event timeline for trace-backed evidence.",
  rules: [
    "Send emails using the provided interface.",
    "Chat with the agent using the provided interface.",
    "Observe the protected data revealed in the assistant's output.",
  ],
  learningGoals: [
    "Explain indirect prompt injection.",
    "Identify how untrusted external content can cross a trust boundary.",
    "Show how retrieved content can influence an agent's behavior.",
    "Use trace evidence to support a security finding.",
    "Propose mitigations involving instruction/data separation, least privilege, and disclosure controls.",
  ],
  objective:
    "Cause the assistant to reveal the target information through the email-based attack path.",
  target: "Manager's home address",
  attackVector: "Email inbox",
  successCriteria: [
    "Send a malicious email to the inbox.",
    "Get the assistant to read or process that email.",
    "Observe the protected data revealed in assistant output.",
  ],
  evidence: [
    "The malicious email payload",
    "The victim prompt or interaction that caused the assistant to process the email",
    "The email-read or context-ingestion event",
    "Relevant tool call or trace evidence",
    "The sensitive-data disclosure event",
    "The final leaked assistant response",
  ],
};

const LAB_2_BRIEFING: BriefingContent = {
  title: "Lab 2: Tool Misuse & Excessive Agency",
  oneLiner: "Abuse agent tool access through deceptive user instructions.",
  estimatedTime: "15-25 min",
  topic: "Tool Misuse",
  missionOverview:
    "You are assessing an operations agent with access to internal action tools and broad task autonomy.",
  scenario:
    "The assistant can trigger operational actions on behalf of a user. You will steer it into unsafe or policy-violating tool behavior using crafted prompts.",
  systemContext:
    "The runtime includes agent chat, tool invocation traces, and event logs for evidence capture.",
  rules: [
    "Allowed: interact through chat and observe tool/event traces.",
    "Not allowed: backend modification, bypassing the UI, or out-of-scope access.",
    "Treat the lab as a controlled educational cyber range.",
  ],
  learningGoals: [
    "Identify excessive-agency and over-permissioned tool patterns.",
    "Demonstrate unsafe tool execution caused by prompt manipulation.",
    "Recommend practical guardrails for tool authorization and confirmation.",
  ],
  objective: "Cause the agent to perform an unsafe tool action",
  target: "Protected operational workflow",
  attackVector: "Agent chat prompts",
  successCriteria: [
    "Send deceptive prompts that request high-risk actions.",
    "Get the agent to attempt or execute an unsafe tool operation.",
    "Observe a policy-violating tool-use outcome in the trace/output.",
  ],
  evidence: [
    "Deceptive prompt payload",
    "Tool-selection or tool-invocation event",
    "Unsafe action attempt/execution event",
    "Final assistant response confirming the action",
  ],
};

const LAB_3_BRIEFING: BriefingContent = {
  title: "Lab 3: Memory & Context Poisoning",
  oneLiner:
    "Poison agent memory/context to influence future behavior and outputs.",
  estimatedTime: "15-25 min",
  topic: "Memory Poisoning",
  missionOverview:
    "You are evaluating an agent that stores and reuses prior context to complete later tasks.",
  scenario:
    "The assistant persists user-supplied context and later treats it as trusted. You will inject poisoned memory so future decisions follow attacker intent.",
  systemContext:
    "The runtime includes agent chat, memory/context events, and timeline traces for verification.",
  rules: [
    "Allowed: submit context, interact through chat, inspect events/traces.",
    "Not allowed: backend modification, bypassing the UI, or out-of-scope access.",
    "Treat the lab as a controlled educational cyber range.",
  ],
  learningGoals: [
    "Explain long-lived context poisoning risk in agent systems.",
    "Demonstrate malicious persistence across interaction turns.",
    "Propose mitigations for memory trust and validation boundaries.",
  ],
  objective: "Persist malicious context that changes later agent behavior",
  target: "Sensitive decision path or protected data flow",
  attackVector: "Stored memory/context channel",
  successCriteria: [
    "Inject poisoned context into memory.",
    "Get the agent to reuse that context in a later step.",
    "Observe attacker-influenced behavior or disclosure in output.",
  ],
  evidence: [
    "Poisoning payload artifact",
    "Memory-write or context-ingestion event",
    "Memory-read/reuse event",
    "Final compromised assistant response",
  ],
};

function resolveBriefing(lab: LabCatalogItem | null): BriefingContent {
  if (!lab) return DEFAULT_BRIEFING;
  if (lab.slug === "agent-prompt-injection") return LAB_1_BRIEFING;
  if (lab.slug === "agent-tool-misuse") return LAB_2_BRIEFING;
  if (lab.slug === "agent-memory-poisoning") return LAB_3_BRIEFING;
  return {
    ...DEFAULT_BRIEFING,
    title: lab.name,
    oneLiner: lab.summary,
  };
}

function MetadataPill({
  icon: Icon,
  label,
  value,
}: {
  icon: ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="inline-flex items-center gap-3 rounded-lg border border-lime-500/20 bg-slate-950/70 px-4 py-2.5 text-sm text-slate-300 shadow-[0_0_18px_rgba(132,204,22,0.05)]">
      <Icon className="h-4 w-4 text-lime-300" />
      <span>
        <span className="text-slate-400">{label}: </span>
        <span className="font-bold text-lime-300">{value}</span>
      </span>
    </div>
  );
}

function BriefingRow({ section }: { section: BriefingSection }) {
  const Icon = section.icon;

  return (
    <section className="grid gap-4 border-b border-lime-500/15 p-5 last:border-b-0 md:grid-cols-[64px_1fr]">
      <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-lime-400/30 bg-lime-500/10 text-lime-300 shadow-[0_0_22px_rgba(132,204,22,0.10)]">
        <Icon className="h-7 w-7" />
      </div>

      <div>
        <h2
          className="text-xl font-extrabold tracking-tight text-slate-100"
          style={{ color: "#f8fafc" }}
        >
          {section.number}. {section.title}
        </h2>

        <div className="mt-2 max-w-4xl text-[15px] leading-7 text-slate-300">
          {section.content}
        </div>
      </div>
    </section>
  );
}

function ToolPill({ icon: Icon, label }: { icon: ElementType; label: string }) {
  return (
    <div className="flex min-w-0 items-center justify-center gap-2 rounded-lg border border-lime-500/20 bg-black/35 px-4 py-3 text-sm font-semibold text-slate-300">
      <Icon className="h-5 w-5 shrink-0 text-lime-300" />
      <span className="truncate">{label}</span>
    </div>
  );
}

function SummaryRow({
  icon: Icon,
  label,
  children,
}: {
  icon: ElementType;
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="grid grid-cols-[44px_1fr] gap-4 border-b border-lime-500/15 p-4 last:border-b-0">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg text-lime-300">
        <Icon className="h-6 w-6" />
      </div>

      <div className="grid gap-1 sm:grid-cols-[150px_1fr]">
        <div className="text-xs font-extrabold uppercase tracking-wide text-lime-300">
          {label}
        </div>
        <div className="text-sm leading-6 text-slate-200">{children}</div>
      </div>
    </div>
  );
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
  const [acknowledged, setAcknowledged] = useState(false);

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

  const briefingSections = useMemo<BriefingSection[]>(
    () => [
      {
        number: 1,
        title: "Mission Overview",
        icon: Target,
        content: <p>{briefing.missionOverview}</p>,
      },
      {
        number: 2,
        title: "Scenario",
        icon: Mail,
        content: <p>{briefing.scenario}</p>,
      },
      {
        number: 3,
        title: "System Context",
        icon: Search,
        content: <p>{briefing.systemContext}</p>,
      },
      {
        number: 4,
        title: "Your Objective",
        icon: Flag,
        content: (
          <p className="font-bold text-lime-300">{briefing.objective}</p>
        ),
      },
      {
        number: 5,
        title: "Rules of Engagement",
        icon: ClipboardList,
        content: (
          <ul className="list-disc space-y-1 pl-5 marker:text-lime-300">
            {briefing.rules.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>
        ),
      },
      {
        number: 6,
        title: "Learning Goals",
        icon: GraduationCap,
        content: (
          <ul className="list-disc space-y-1 pl-5 marker:text-lime-300">
            {briefing.learningGoals.map((goal) => (
              <li key={goal}>{goal}</li>
            ))}
          </ul>
        ),
      },
    ],
    [briefing],
  );

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
      rememberLatestSessionForLab(labId, sessionId);
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

  return (
    <div className="min-h-screen overflow-hidden bg-black font-sans text-slate-100 antialiased">
      <div className="relative min-h-screen">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_5%,rgba(132,204,22,0.12),transparent_32%),radial-gradient(circle_at_90%_20%,rgba(34,197,94,0.12),transparent_28%),linear-gradient(180deg,#020617_0%,#020617_48%,#000_100%)]" />
        <div className="pointer-events-none absolute inset-0 opacity-[0.08]">
          <div className="h-full w-full bg-[linear-gradient(rgba(132,204,22,0.30)_1px,transparent_1px),linear-gradient(90deg,rgba(132,204,22,0.20)_1px,transparent_1px)] bg-[size:44px_44px]" />
        </div>

        <header className="relative z-10 border-b border-lime-500/15 bg-black/40 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 md:px-8 lg:px-10">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-lime-500/15 text-lime-300 ring-1 ring-lime-400/40 shadow-[0_0_24px_rgba(132,204,22,0.22)]">
                <Shield className="h-7 w-7" />
              </div>

              <div>
                <div className="text-sm font-black uppercase tracking-[0.22em] text-slate-100">
                  Agent Failure
                </div>
                <div className="text-xs font-medium text-slate-500">
                  AI Agent Security Labs
                </div>
              </div>
            </div>

            <nav className="hidden items-center gap-5 text-sm font-semibold text-slate-300 sm:flex">
              <span className="inline-flex items-center gap-2">
                <HelpCircle className="h-4 w-4" />
                Help
              </span>
              <span className="h-5 w-px bg-lime-500/20" />
              <span className="inline-flex items-center gap-2">
                <BookOpen className="h-4 w-4" />
                Lab Guide
              </span>
            </nav>
          </div>
        </header>

        <main className="relative z-10 mx-auto max-w-7xl px-5 py-8 md:px-8 lg:px-10">
          <section className="grid gap-7 lg:grid-cols-[1fr_500px] lg:items-start">
            <section className="overflow-hidden rounded-3xl border border-lime-500/20 bg-slate-950/70 backdrop-blur">
              <div className="border-b border-lime-500/15 px-5 py-5">
                <h1
                  className="text-3xl font-black tracking-tight text-slate-100 md:text-4xl"
                  style={{ color: "#f8fafc" }}
                >
                  {labName}
                </h1>
                <p className="mt-3 max-w-4xl text-[15px] leading-7 text-slate-300">
                  {briefing.oneLiner}
                </p>

                <div className="mt-4 flex flex-wrap gap-3">
                  <MetadataPill
                    icon={Tag}
                    label="Difficulty"
                    value={difficulty}
                  />
                  <MetadataPill
                    icon={Clock}
                    label="Estimated"
                    value={briefing.estimatedTime}
                  />
                  <MetadataPill
                    icon={Radar}
                    label="Topic"
                    value={briefing.topic}
                  />
                </div>
              </div>

              <div>
                {briefingSections.map((section) => (
                  <BriefingRow key={section.title} section={section} />
                ))}
              </div>

              <div className="border-t border-lime-500/15 p-5">
                <h3
                  className="mb-3 text-sm font-black uppercase tracking-wide text-lime-300"
                  style={{ color: "#86efac" }}
                >
                  Available Lab Tools
                </h3>
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  <ToolPill icon={MessageCircle} label="Agent Chat" />
                  <ToolPill icon={Mail} label="Email Inbox" />
                  <ToolPill icon={BarChart3} label="Event Timeline" />
                  <ToolPill icon={Wifi} label="Trace Stream" />
                </div>
              </div>
            </section>

            <aside className="relative overflow-hidden rounded-3xl border border-lime-400/50 bg-slate-950/75 p-6 shadow-[0_0_46px_rgba(132,204,22,0.18)] backdrop-blur lg:sticky lg:top-8 lg:self-start">
              <div className="pointer-events-none absolute inset-0 opacity-25">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(132,204,22,0.25),transparent_42%)]" />
                <div className="absolute right-0 top-0 h-full w-full bg-[linear-gradient(rgba(132,204,22,0.13)_1px,transparent_1px),linear-gradient(90deg,rgba(132,204,22,0.13)_1px,transparent_1px)] bg-[size:32px_32px]" />
              </div>

              <div className="relative">
                <div className="mb-6 flex items-center gap-4">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-lime-500/10 text-lime-300 ring-1 ring-lime-400/40 shadow-[0_0_22px_rgba(132,204,22,0.20)]">
                    <Radar className="h-7 w-7" />
                  </div>
                  <h2
                    className="text-2xl font-black uppercase tracking-wide text-lime-300"
                    style={{ color: "#86efac" }}
                  >
                    Mission Summary
                  </h2>
                </div>

                <div className="overflow-hidden rounded-2xl border border-lime-500/20 bg-black/25">
                  <SummaryRow icon={Target} label="Objective">
                    {briefing.objective}
                  </SummaryRow>

                  <SummaryRow icon={User} label="Target">
                    {briefing.target}
                  </SummaryRow>

                  <SummaryRow icon={Mail} label="Attack Vector">
                    {briefing.attackVector}
                  </SummaryRow>

                  <div className="grid grid-cols-[44px_1fr] gap-4 border-b border-lime-500/15 p-4">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg text-lime-300">
                      <CheckSquare className="h-6 w-6" />
                    </div>

                    <div>
                      <div className="text-xs font-extrabold uppercase tracking-wide text-lime-300">
                        Success Criteria
                      </div>

                      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-200 marker:text-lime-300">
                        {briefing.successCriteria.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="grid grid-cols-[44px_1fr] gap-4 p-4">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg text-lime-300">
                      <Camera className="h-6 w-6" />
                    </div>

                    <div>
                      <div className="text-xs font-extrabold uppercase tracking-wide text-lime-300">
                        Evidence to Capture
                      </div>

                      <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-slate-200 marker:text-lime-300">
                        {briefing.evidence.map((entry) => (
                          <li key={entry}>{entry}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>

                <label className="mt-6 flex items-center cursor-pointer gap-4 rounded-2xl border border-lime-500/15 bg-black/25 p-4 text-sm leading-6 text-slate-200 transition hover:border-lime-400/40 hover:bg-lime-500/5">
                  <input
                    type="checkbox"
                    checked={acknowledged}
                    onChange={(event) => setAcknowledged(event.target.checked)}
                    className="sr-only"
                  />
                  <span
                    className={[
                      "flex h-6 w-6 shrink-0 items-center justify-center rounded-sm border transition",
                      acknowledged
                        ? "border-lime-300 bg-lime-300 text-black shadow-[0_0_16px_rgba(132,204,22,0.45)]"
                        : "border-lime-400/70 bg-black/50 text-transparent",
                    ].join(" ")}
                  >
                    <Check className="h-4 w-4" />
                  </span>
                  <span>I understand the task</span>
                </label>

                <button
                  type="button"
                  disabled={starting || !acknowledged}
                  onClick={() => void onStartLab()}
                  className="mt-5 flex h-14 w-full items-center justify-center gap-3 rounded-xl bg-lime-300 text-base font-black uppercase tracking-wide text-black shadow-[0_0_30px_rgba(132,204,22,0.55)] transition hover:bg-lime-200 hover:shadow-[0_0_44px_rgba(132,204,22,0.75)] disabled:cursor-not-allowed disabled:opacity-70"
                >
                  <Play className="h-5 w-5 fill-black" />
                  {starting ? "Starting Lab..." : "Start Lab"}
                </button>

                <button
                  type="button"
                  onClick={() => navigate("/labs")}
                  className="mt-4 flex h-12 w-full items-center justify-center gap-3 rounded-xl border border-lime-400/50 bg-black/30 text-sm font-extrabold uppercase tracking-wide text-lime-300 transition hover:bg-lime-500/10 hover:text-lime-200"
                >
                  <ArrowLeft className="h-5 w-5" />
                  Back to Catalog
                </button>

                {startError ? (
                  <p className="mt-3 text-sm text-rose-300">{startError}</p>
                ) : null}
              </div>
            </aside>
          </section>
        </main>

        <footer className="relative z-10 border-t border-lime-500/15 bg-black/30 py-4">
          <div className="mx-auto flex max-w-7xl items-center justify-between px-5 text-xs text-slate-500 md:px-8 lg:px-10">
            <span className="inline-flex items-center gap-2">
              <Lock className="h-3.5 w-3.5" />
              Controlled educational environment
            </span>
            <span>Agent Failure Labs</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
