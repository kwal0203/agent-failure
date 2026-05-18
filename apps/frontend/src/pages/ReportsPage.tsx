import {
  BarChart3,
  Bell,
  BookOpen,
  Boxes,
  Brain,
  ClipboardCheck,
  ExternalLink,
  FileText,
  GraduationCap,
  Home,
  Landmark,
  LifeBuoy,
  ListChecks,
  MessageSquareWarning,
  Network,
  Search,
  Shield,
  Target,
  Users,
  Wrench,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/context";
import { useShellBootstrap } from "../shell/context";
import {
  getLatestSessionIdForLab,
  type LabCatalogItem,
  loadLabCatalog,
} from "./labCatalogApi";

type CatalogModule = {
  id: string;
  number?: number;
  title: string;
  status: "Pilot Ready" | "Available" | "In Development" | "Planned";
  description: string;
  difficulty: "Beginner" | "Intermediate" | "Advanced";
  exerciseCount: number;
  primaryType: "Full Lab" | "Micro-Lab" | "Trace" | "Assessment";
  icon: React.ElementType;
  iconTone: string;
  statusTone: string;
  isReportEnabled: boolean;
};

const navItems = [
  { label: "Dashboard", icon: Home },
  { label: "Catalog", icon: BookOpen },
  { label: "Courses", icon: GraduationCap },
  { label: "Reports", icon: BarChart3 },
  { label: "Instructor View", icon: Users },
];

const resourceItems = [
  { label: "Standards", icon: Shield },
  { label: "Documentation", icon: FileText },
  { label: "Community", icon: Users },
  { label: "Support", icon: LifeBuoy },
];

const modules: CatalogModule[] = [
  {
    id: "foundations",
    number: 1,
    title: "Foundations of AI Agent Security",
    status: "Planned",
    description: "Agent architecture primer, threat modeling, trace reading",
    difficulty: "Beginner",
    exerciseCount: 4,
    primaryType: "Full Lab",
    icon: Shield,
    iconTone: "bg-lime-950/80 text-lime-300 ring-lime-500/40",
    statusTone: "bg-slate-700/60 text-slate-300 ring-slate-500/30",
    isReportEnabled: false,
  },
  {
    id: "indirect-prompt-injection",
    number: 2,
    title: "Indirect Prompt Injection",
    status: "Available",
    description: "OpsMail Assistant",
    difficulty: "Intermediate",
    exerciseCount: 4,
    primaryType: "Full Lab",
    icon: MessageSquareWarning,
    iconTone: "bg-lime-950/80 text-lime-300 ring-lime-500/40",
    statusTone: "bg-lime-500/15 text-lime-300 ring-lime-400/30",
    isReportEnabled: false,
  },
  {
    id: "tool-misuse",
    number: 3,
    title: "Tool Misuse & Excessive Agency",
    status: "Available",
    description: "SRE Runbook Agent",
    difficulty: "Intermediate",
    exerciseCount: 4,
    primaryType: "Full Lab",
    icon: Wrench,
    iconTone: "bg-lime-950/80 text-lime-300 ring-lime-500/40",
    statusTone: "bg-lime-500/15 text-lime-300 ring-lime-400/30",
    isReportEnabled: false,
  },
  {
    id: "memory-poisoning",
    number: 4,
    title: "Memory & Context Poisoning",
    status: "Available",
    description: "Invoice Payment Agent",
    difficulty: "Intermediate",
    exerciseCount: 4,
    primaryType: "Full Lab",
    icon: Brain,
    iconTone: "bg-lime-950/80 text-lime-300 ring-lime-500/40",
    statusTone: "bg-lime-500/15 text-lime-300 ring-lime-400/30",
    isReportEnabled: false,
  },
  {
    id: "multi-agent",
    number: 5,
    title: "Multi-Agent & Delegated Authority",
    status: "Planned",
    description: "Cross-agent trust and confused deputy behavior",
    difficulty: "Advanced",
    exerciseCount: 4,
    primaryType: "Full Lab",
    icon: Network,
    iconTone: "bg-yellow-950/70 text-yellow-300 ring-yellow-500/40",
    statusTone: "bg-slate-700/60 text-slate-300 ring-slate-500/30",
    isReportEnabled: false,
  },
  {
    id: "observability",
    number: 6,
    title: "Observability & Accountability",
    status: "Planned",
    description: "Trace review and incident reconstruction",
    difficulty: "Intermediate",
    exerciseCount: 3,
    primaryType: "Trace",
    icon: Search,
    iconTone: "bg-lime-950/80 text-lime-300 ring-lime-500/40",
    statusTone: "bg-slate-700/60 text-slate-300 ring-slate-500/30",
    isReportEnabled: false,
  },
  {
    id: "supply-chain",
    number: 7,
    title: "Agent Supply Chain & Tool Manifests",
    status: "Planned",
    description: "Tool manifest and MCP server review",
    difficulty: "Advanced",
    exerciseCount: 3,
    primaryType: "Trace",
    icon: Boxes,
    iconTone: "bg-violet-950/70 text-violet-300 ring-violet-500/40",
    statusTone: "bg-slate-700/60 text-slate-300 ring-slate-500/30",
    isReportEnabled: false,
  },
  {
    id: "capstone",
    number: 8,
    title: "Capstone: Multi-Stage Agent Compromise",
    status: "Planned",
    description: "Final incident and report",
    difficulty: "Advanced",
    exerciseCount: 5,
    primaryType: "Full Lab",
    icon: Target,
    iconTone: "bg-yellow-950/70 text-yellow-300 ring-yellow-500/40",
    statusTone: "bg-slate-700/60 text-slate-300 ring-slate-500/30",
    isReportEnabled: false,
  },
];

function canViewPilotRequests(): boolean {
  const rawTokens = window.sessionStorage.getItem("agentfailure.auth.tokens");
  if (!rawTokens) return false;
  try {
    const parsed = JSON.parse(rawTokens) as { idToken?: string };
    if (!parsed.idToken) return false;
    const parts = parsed.idToken.split(".");
    if (parts.length < 2) return false;
    const payload = JSON.parse(
      atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")),
    ) as Record<string, unknown>;
    const groups = payload?.["cognito:groups"];
    return (
      Array.isArray(groups) &&
      (groups.includes("admin") || groups.includes("staff"))
    );
  } catch {
    return false;
  }
}

function getModuleLab(
  moduleId: string,
  labs: LabCatalogItem[],
): LabCatalogItem | null {
  const findBySlug = (slug: string) => labs.find((lab) => lab.slug === slug);
  if (moduleId === "indirect-prompt-injection") {
    return findBySlug("agent-prompt-injection") ?? null;
  }
  if (moduleId === "tool-misuse") {
    return findBySlug("agent-tool-misuse") ?? null;
  }
  if (moduleId === "memory-poisoning") {
    return findBySlug("agent-memory-poisoning") ?? null;
  }
  return null;
}

function Sidebar({
  activeLabel,
  onNavigate,
}: {
  activeLabel: string;
  onNavigate: (label: string) => void;
}) {
  return (
    <aside className="relative z-20 flex w-64 min-w-64 shrink-0 flex-col border-r border-lime-500/20 bg-black/80">
      <div className="flex h-20 items-center gap-3 border-b border-lime-500/20 px-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-lime-500/15 text-lime-300 ring-1 ring-lime-400/40 shadow-[0_0_22px_rgba(132,204,22,0.25)]">
          <Shield className="h-6 w-6" />
        </div>
        <span className="text-xl font-extrabold tracking-tight text-slate-100">
          Agent Failure
        </span>
      </div>
      <nav className="space-y-1 px-4 py-4">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.label}
              type="button"
              onClick={() => onNavigate(item.label)}
              className={[
                "relative flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold transition",
                item.label === activeLabel
                  ? "border border-lime-400/40 bg-lime-500/10 text-lime-200 shadow-[0_0_18px_rgba(132,204,22,0.18)] before:absolute before:left-0 before:top-1/2 before:h-8 before:w-1 before:-translate-y-1/2 before:rounded-full before:bg-lime-400 before:shadow-[0_0_16px_rgba(132,204,22,0.9)]"
                  : "text-slate-300 hover:bg-lime-500/5 hover:text-lime-200",
              ].join(" ")}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </button>
          );
        })}
      </nav>
      <div className="px-4 py-5">
        <div className="mb-5 border-t border-lime-500/20" />
        <p className="mb-3 px-4 text-xs font-bold uppercase tracking-wide text-slate-500">
          Resources
        </p>
        <div className="space-y-1">
          {resourceItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.label}
                type="button"
                className="flex w-full items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-300 transition hover:bg-lime-500/5 hover:text-lime-200"
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </div>
        <div className="mt-8 border-t border-lime-500/20 pt-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-lime-500/10 text-lime-300 ring-1 ring-lime-400/40">
              <Landmark className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-lime-300/70">
                Northwood
              </p>
              <p className="text-sm font-extrabold leading-tight text-lime-200">
                University
              </p>
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}

export default function ReportsPage() {
  const bootstrap = useShellBootstrap();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [labs, setLabs] = useState<LabCatalogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [latestSessionByLab, setLatestSessionByLab] = useState<
    Record<string, string>
  >({});
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement | null>(null);
  const showPilotRequestsLink = useMemo(() => canViewPilotRequests(), []);

  const refreshLabs = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      setLabs(await loadLabCatalog(bootstrap.apiBaseUrl));
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : "Failed to load labs",
      );
      setLabs([]);
    } finally {
      setIsLoading(false);
    }
  }, [bootstrap.apiBaseUrl]);

  useEffect(() => {
    void refreshLabs();
  }, [refreshLabs]);

  useEffect(() => {
    if (labs.length < 1) {
      setLatestSessionByLab({});
      return;
    }

    let cancelled = false;
    const loadLatestSessions = async () => {
      const mappedLabs = modules
        .map((module) => getModuleLab(module.id, labs))
        .filter((lab): lab is LabCatalogItem => lab !== null);
      const uniqueLabs = Array.from(
        new Map(mappedLabs.map((lab) => [lab.id, lab])).values(),
      );
      const entries = await Promise.all(
        uniqueLabs.map(async (lab) => {
          try {
            const sessionId = await getLatestSessionIdForLab(
              bootstrap.apiBaseUrl,
              lab.id,
            );
            return [lab.id, sessionId] as const;
          } catch {
            return [lab.id, null] as const;
          }
        }),
      );
      if (cancelled) return;
      const next: Record<string, string> = {};
      for (const [labId, sessionId] of entries) {
        if (typeof sessionId === "string" && sessionId.length > 0) {
          next[labId] = sessionId;
        }
      }
      setLatestSessionByLab(next);
    };

    void loadLatestSessions();
    return () => {
      cancelled = true;
    };
  }, [bootstrap.apiBaseUrl, labs]);

  useEffect(() => {
    if (bootstrap.mode !== "demo") {
      return;
    }
    const root = document.documentElement;
    const previousFontSize = root.style.fontSize;
    root.style.fontSize = "17.5px";
    return () => {
      root.style.fontSize = previousFontSize;
    };
  }, [bootstrap.mode]);

  useEffect(() => {
    const handleDocumentClick = (event: MouseEvent) => {
      if (!userMenuRef.current) return;
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (!userMenuRef.current.contains(target)) setIsUserMenuOpen(false);
    };
    document.addEventListener("mousedown", handleDocumentClick);
    return () => {
      document.removeEventListener("mousedown", handleDocumentClick);
    };
  }, []);

  return (
    <div className="h-screen overflow-hidden bg-black font-sans text-slate-100 antialiased">
      <div className="relative flex h-full overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(132,204,22,0.12),transparent_30%),radial-gradient(circle_at_top_right,rgba(34,197,94,0.10),transparent_28%),linear-gradient(180deg,#020617_0%,#020617_40%,#000_100%)]" />
        <Sidebar
          activeLabel="Reports"
          onNavigate={(label) => {
            if (label === "Reports") return;
            if (label === "Catalog") {
              navigate("/labs");
              return;
            }
            if (label === "Dashboard") navigate("/app");
          }}
        />
        <main className="relative flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-10 h-20 border-b border-lime-500/20 bg-black/55 px-5 backdrop-blur md:px-8 lg:px-10">
            <div className="flex h-full items-center justify-between">
              <div />
              <div className="ml-auto flex items-center gap-4">
                <button
                  type="button"
                  className="rounded-full p-2 text-slate-300 transition hover:bg-lime-500/10 hover:text-lime-200"
                  aria-label="Notifications"
                >
                  <Bell className="h-5 w-5" />
                </button>
                <div className="relative pl-1" ref={userMenuRef}>
                  <button
                    type="button"
                    aria-haspopup="menu"
                    aria-expanded={isUserMenuOpen}
                    onClick={() => setIsUserMenuOpen((open) => !open)}
                    className="flex items-center gap-2 rounded-lg px-2 py-1 text-left transition hover:bg-lime-500/10"
                  >
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-800 text-xs font-extrabold text-slate-100 ring-1 ring-lime-500/20">
                      IN
                    </div>
                    <span className="hidden text-sm font-semibold text-slate-300 sm:inline">
                      Instructor
                    </span>
                  </button>
                  {isUserMenuOpen ? (
                    <div
                      role="menu"
                      className="absolute right-0 z-30 mt-2 w-40 rounded-lg border border-lime-500/30 bg-black/95 p-1 shadow-[0_0_20px_rgba(132,204,22,0.18)] backdrop-blur"
                    >
                      {showPilotRequestsLink ? (
                        <button
                          type="button"
                          role="menuitem"
                          onClick={() => {
                            setIsUserMenuOpen(false);
                            navigate("/pilot-requests");
                          }}
                          className="flex w-full items-center rounded-md px-3 py-2 text-sm font-semibold text-slate-200 transition hover:bg-lime-500/10 hover:text-lime-100"
                        >
                          Pilot Requests
                        </button>
                      ) : null}
                      <button
                        type="button"
                        role="menuitem"
                        onClick={() => {
                          setIsUserMenuOpen(false);
                          logout();
                        }}
                        className="flex w-full items-center rounded-md px-3 py-2 text-sm font-semibold text-slate-200 transition hover:bg-lime-500/10 hover:text-lime-100"
                      >
                        Log Out
                      </button>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-7xl px-5 pt-5 pb-8 text-[17px] md:px-8 lg:px-10">
              {isLoading ? (
                <p className="mt-6 text-lime-300/85">
                  Loading reports catalog...
                </p>
              ) : null}
              {loadError ? (
                <p className="mt-4 rounded-lg border border-rose-700/70 bg-rose-950/35 px-3 py-2 text-sm text-rose-200">
                  Error: {loadError}
                </p>
              ) : null}
              {actionError ? (
                <p className="mt-4 rounded-lg border border-amber-700/70 bg-amber-950/30 px-3 py-2 text-sm text-amber-200">
                  {actionError}
                </p>
              ) : null}

              {!isLoading ? (
                <section className="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
                  {modules.map((module) => {
                    const Icon = module.icon;
                    const moduleLab = getModuleLab(module.id, labs);
                    const latestSessionId = moduleLab
                      ? latestSessionByLab[moduleLab.id]
                      : undefined;
                    const isEnabled =
                      !!moduleLab &&
                      typeof latestSessionId === "string" &&
                      latestSessionId.length > 0;

                    return (
                      <article
                        key={module.id}
                        className="group flex min-h-[260px] flex-col rounded-2xl border border-lime-500/20 bg-slate-950/70 p-5 shadow-[0_0_0_1px_rgba(15,23,42,0.8)] backdrop-blur transition hover:-translate-y-0.5 hover:border-lime-400/60 hover:shadow-[0_0_30px_rgba(132,204,22,0.16)]"
                      >
                        <div className="flex items-start gap-4">
                          <div
                            className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-full ring-1 shadow-[0_0_22px_rgba(132,204,22,0.15)] ${module.iconTone}`}
                          >
                            <Icon className="h-7 w-7" />
                          </div>
                          <div className="min-w-0">
                            <h3 className="text-base font-extrabold leading-snug text-slate-100">
                              {module.number}. {module.title}
                            </h3>
                            <div className="mt-3">
                              <span
                                className={`inline-flex w-fit items-center rounded-md px-2.5 py-1 text-xs font-bold ring-1 ${module.statusTone}`}
                              >
                                {module.status}
                              </span>
                            </div>
                          </div>
                        </div>
                        <p className="mt-4 min-h-[44px] text-sm leading-6 text-slate-400">
                          {module.description}
                        </p>
                        <div className="mt-auto flex flex-wrap items-center gap-x-4 gap-y-2 pt-5 text-xs font-medium text-slate-400">
                          <span className="inline-flex items-center gap-1.5">
                            <BarChart3 className="h-4 w-4 text-lime-300/80" />
                            {module.difficulty}
                          </span>
                          <span className="inline-flex items-center gap-1.5">
                            <ListChecks className="h-4 w-4 text-lime-300/80" />
                            {module.exerciseCount} Exercises
                          </span>
                          <span className="inline-flex items-center gap-1.5">
                            <ClipboardCheck className="h-4 w-4 text-lime-300/80" />
                            {module.primaryType}
                          </span>
                        </div>
                        <button
                          type="button"
                          disabled={!isEnabled}
                          onClick={() => {
                            if (!isEnabled || !latestSessionId) {
                              setActionError(
                                "No session found for this module yet. Run the lab first, then open report.",
                              );
                              return;
                            }
                            setActionError(null);
                            navigate(`/sessions/${latestSessionId}/report`);
                          }}
                          className={[
                            "mt-4 inline-flex h-10 items-center justify-center gap-2 rounded-lg border text-sm font-extrabold transition",
                            isEnabled
                              ? "border-lime-400/70 bg-lime-500/10 text-lime-200 hover:bg-lime-400/15 hover:shadow-[0_0_22px_rgba(132,204,22,0.25)]"
                              : "border-lime-500/35 bg-slate-950/60 text-lime-300 opacity-75 cursor-not-allowed",
                          ].join(" ")}
                        >
                          Open Report
                          <ExternalLink className="h-4 w-4" />
                        </button>
                      </article>
                    );
                  })}
                </section>
              ) : null}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
