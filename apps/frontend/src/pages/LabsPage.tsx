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
  type LabCatalogItem,
  type LabDifficulty,
  loadLabCatalog,
} from "./labCatalogApi";

export type { LabCatalogItem, LabDifficulty } from "./labCatalogApi";

type DifficultyChoice = LabDifficulty | "hard";

type LabCatalogProps = {
  apiBaseUrl: string;
  learnerLabel: string;
  mode?: "demo" | "debug";
  loadLabs?: (apiBaseUrl: string) => Promise<LabCatalogItem[]>;
  onOpenPreLab: (selection: {
    labId: string;
    labName: string;
    labSlug: string;
    labSummary: string;
    labDifficulty: LabDifficulty;
  }) => void;
};

type ModuleStatus = "Pilot Ready" | "Available" | "In Development" | "Planned";
type ExerciseType = "Full Lab" | "Micro-Lab" | "Trace" | "Assessment";

type CatalogModule = {
  id: string;
  number?: number;
  title: string;
  status: ModuleStatus;
  description: string;
  difficulty: "Beginner" | "Intermediate" | "Advanced";
  exerciseCount: number;
  primaryType: ExerciseType;
  icon: React.ElementType;
  iconTone: string;
  statusTone: string;
  action: "Open Module";
  isLaunchEnabled: boolean;
};

type StoredAuthTokens = {
  idToken?: string;
};

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(payload)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function canViewPilotRequests(): boolean {
  const rawTokens = window.sessionStorage.getItem("agentfailure.auth.tokens");
  if (!rawTokens) return false;
  try {
    const parsed = JSON.parse(rawTokens) as StoredAuthTokens;
    if (!parsed.idToken) return false;
    const payload = decodeJwtPayload(parsed.idToken);
    const groups = payload?.["cognito:groups"];
    if (!Array.isArray(groups)) return false;
    return groups.includes("admin") || groups.includes("staff");
  } catch {
    return false;
  }
}

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
    action: "Open Module",
    isLaunchEnabled: false,
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
    action: "Open Module",
    isLaunchEnabled: true,
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
    action: "Open Module",
    isLaunchEnabled: true,
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
    action: "Open Module",
    isLaunchEnabled: true,
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
    action: "Open Module",
    isLaunchEnabled: false,
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
    action: "Open Module",
    isLaunchEnabled: false,
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
    action: "Open Module",
    isLaunchEnabled: false,
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
    action: "Open Module",
    isLaunchEnabled: false,
  },
];

function getCardDifficulty(
  selectedByLab: Record<string, DifficultyChoice>,
  labId: string,
): DifficultyChoice {
  return selectedByLab[labId] ?? "medium";
}

function StatusBadge({
  label,
  className,
}: {
  label: string;
  className: string;
}) {
  return (
    <span
      className={`inline-flex w-fit items-center rounded-md px-2.5 py-1 text-xs font-bold ring-1 ${className}`}
    >
      {label}
    </span>
  );
}

function ModuleCard({
  module,
  onOpen,
}: {
  module: CatalogModule;
  onOpen: (() => void) | null;
}) {
  const Icon = module.icon;
  const isEnabled = module.isLaunchEnabled && onOpen !== null;

  return (
    <article className="group flex min-h-[260px] flex-col rounded-2xl border border-lime-500/20 bg-slate-950/70 p-5 shadow-[0_0_0_1px_rgba(15,23,42,0.8)] backdrop-blur transition hover:-translate-y-0.5 hover:border-lime-400/60 hover:shadow-[0_0_30px_rgba(132,204,22,0.16)]">
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
            <StatusBadge label={module.status} className={module.statusTone} />
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
        onClick={onOpen ?? undefined}
        disabled={!isEnabled}
        className={[
          "mt-4 inline-flex h-10 items-center justify-center gap-2 rounded-lg border text-sm font-extrabold transition",
          isEnabled
            ? "border-lime-400/70 bg-lime-500/10 text-lime-200 hover:bg-lime-400/15 hover:shadow-[0_0_22px_rgba(132,204,22,0.25)]"
            : "border-lime-500/35 bg-slate-950/60 text-lime-300 opacity-75",
          isEnabled ? "" : "cursor-not-allowed",
        ].join(" ")}
      >
        {module.action}
        <ExternalLink className="h-4 w-4" />
      </button>
    </article>
  );
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
        <span
          className="text-xl font-extrabold tracking-tight text-slate-100"
          style={{ color: "#f8fafc" }}
        >
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

function getModuleLab(
  moduleId: string,
  labs: LabCatalogItem[],
): LabCatalogItem | null {
  if (labs.length === 0) {
    return null;
  }
  const findBySlug = (slug: string) => labs.find((lab) => lab.slug === slug);
  if (moduleId === "foundations") {
    return findBySlug("agent-prompt-injection") ?? labs[0] ?? null;
  }
  if (moduleId === "indirect-prompt-injection") {
    return findBySlug("agent-prompt-injection") ?? null;
  }
  if (moduleId === "tool-misuse") {
    return findBySlug("agent-tool-misuse") ?? null;
  }
  if (moduleId === "memory-poisoning") {
    return findBySlug("agent-memory-poisoning") ?? null;
  }
  if (moduleId === "observability") {
    return labs[1] ?? labs[0] ?? null;
  }
  return null;
}

export function LabCatalog({
  apiBaseUrl,
  learnerLabel,
  mode = "demo",
  loadLabs = loadLabCatalog,
  onOpenPreLab,
}: LabCatalogProps) {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [labs, setLabs] = useState<LabCatalogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [launchingLabId, setLaunchingLabId] = useState<string | null>(null);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [selectedDifficulty, setSelectedDifficulty] =
    useState<DifficultyChoice>("medium");
  const [selectedDifficultyByLab] = useState<Record<string, DifficultyChoice>>(
    {},
  );
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement | null>(null);
  const showPilotRequestsLink = useMemo(() => canViewPilotRequests(), []);

  const refreshLabs = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const loadedLabs = await loadLabs(apiBaseUrl);
      setLabs(loadedLabs);
    } catch (error) {
      setLoadError(
        error instanceof Error ? error.message : "Failed to load lab catalog",
      );
      setLabs([]);
    } finally {
      setIsLoading(false);
    }
  }, [apiBaseUrl, loadLabs]);

  useEffect(() => {
    void refreshLabs();
  }, [refreshLabs]);

  useEffect(() => {
    if (mode !== "demo") {
      return;
    }
    const root = document.documentElement;
    const previousFontSize = root.style.fontSize;
    root.style.fontSize = "17.5px";
    return () => {
      root.style.fontSize = previousFontSize;
    };
  }, [mode]);

  useEffect(() => {
    const handleDocumentClick = (event: MouseEvent) => {
      if (!userMenuRef.current) {
        return;
      }
      const target = event.target;
      if (!(target instanceof Node)) {
        return;
      }
      if (!userMenuRef.current.contains(target)) {
        setIsUserMenuOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsUserMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleDocumentClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleDocumentClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  const launchLab = (labId: string) => {
    const chosenDifficulty =
      mode === "debug"
        ? selectedDifficulty
        : getCardDifficulty(selectedDifficultyByLab, labId);
    if (chosenDifficulty === "easy" || chosenDifficulty === "hard") {
      setLaunchError("Easy and Hard difficulties are not available yet.");
      return;
    }
    const selectedLab = labs.find((lab) => lab.id === labId);
    if (!selectedLab) {
      setLaunchError("Selected lab could not be loaded.");
      return;
    }
    setLaunchingLabId(labId);
    setLaunchError(null);
    onOpenPreLab({
      labId: selectedLab.id,
      labName: selectedLab.name,
      labSlug: selectedLab.slug,
      labSummary: selectedLab.summary,
      labDifficulty: chosenDifficulty,
    });
  };

  if (mode === "debug") {
    return (
      <section>
        <h1 style={{ margin: "0 0 12px" }}>Labs</h1>
        <p style={{ margin: "0 0 14px" }}>
          Demo shell is active for <strong>{learnerLabel}</strong>.
        </p>
        <label
          htmlFor="lab-difficulty"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            margin: "0 0 14px",
          }}
        >
          Difficulty
          <select
            id="lab-difficulty"
            value={selectedDifficulty}
            onChange={(event) =>
              setSelectedDifficulty(event.target.value as DifficultyChoice)
            }
            disabled={launchingLabId !== null}
          >
            <option value="medium">Medium</option>
            <option value="easy" disabled>
              Easy (Coming soon)
            </option>
            <option value="hard">Hard (Coming soon)</option>
          </select>
        </label>

        {isLoading && (
          <p style={{ margin: "0 0 12px" }}>Loading lab catalog...</p>
        )}

        {loadError && (
          <div
            style={{
              border: "1px solid #fecaca",
              background: "#fff1f2",
              borderRadius: 10,
              padding: 12,
              marginBottom: 12,
              maxWidth: 800,
            }}
          >
            <p style={{ margin: "0 0 8px", color: "#9f1239" }}>
              Error: {loadError}
            </p>
            <button type="button" onClick={() => void refreshLabs()}>
              Retry
            </button>
          </div>
        )}

        {!isLoading && !loadError && labs.length === 0 && (
          <div
            style={{
              border: "1px solid #cdd5e2",
              borderRadius: 10,
              background: "#fff",
              padding: 16,
              maxWidth: 800,
            }}
          >
            <p style={{ margin: 0 }}>
              No launchable labs are currently available.
            </p>
          </div>
        )}

        {!isLoading && !loadError && labs.length > 0 && (
          <div
            style={{
              display: "grid",
              gap: 12,
              maxWidth: 900,
              margin: "0 auto",
            }}
          >
            {labs.map((lab) => {
              const isLaunchingThisLab = launchingLabId === lab.id;
              return (
                <article
                  key={lab.id}
                  style={{
                    border: "1px solid #cdd5e2",
                    borderRadius: 10,
                    background: "#fff",
                    padding: 16,
                    textAlign: "left",
                  }}
                >
                  <h2 style={{ margin: "0 0 8px", fontSize: 20 }}>
                    {lab.name}
                  </h2>
                  <p style={{ margin: "0 0 8px", opacity: 0.9 }}>
                    {lab.summary}
                  </p>
                  <p style={{ margin: "0 0 10px", fontSize: 13, opacity: 0.8 }}>
                    slug: <code>{lab.slug}</code>
                  </p>
                  <p style={{ margin: "0 0 12px", fontSize: 13 }}>
                    resume: {lab.capabilities.supports_resume ? "yes" : "no"} |
                    uploads: {lab.capabilities.supports_uploads ? "yes" : "no"}
                  </p>
                  <button
                    type="button"
                    onClick={() => launchLab(lab.id)}
                    disabled={launchingLabId !== null}
                  >
                    {isLaunchingThisLab ? "Opening briefing..." : "Launch lab"}
                  </button>
                </article>
              );
            })}
          </div>
        )}

        {launchError && (
          <p style={{ margin: "12px 0 0", color: "#9f1239" }}>
            Session launch error: {launchError}
          </p>
        )}
      </section>
    );
  }

  return (
    <div className="h-screen overflow-hidden bg-black font-sans text-slate-100 antialiased">
      <div className="relative flex h-full overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(132,204,22,0.12),transparent_30%),radial-gradient(circle_at_top_right,rgba(34,197,94,0.10),transparent_28%),linear-gradient(180deg,#020617_0%,#020617_40%,#000_100%)]" />

        <div className="pointer-events-none absolute top-0 right-8 hidden h-80 w-96 opacity-20 lg:block">
          <div className="h-full w-full bg-[linear-gradient(180deg,rgba(132,204,22,0.35)_1px,transparent_1px)] bg-[size:18px_18px]" />
        </div>

        <Sidebar
          activeLabel="Catalog"
          onNavigate={(label) => {
            if (label === "Catalog") return;
            if (label === "Reports") {
              navigate("/reports");
              return;
            }
            if (label === "Dashboard") {
              navigate("/app");
            }
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

                  {isUserMenuOpen && (
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
                  )}
                </div>
              </div>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-7xl px-5 pt-5 pb-8 text-[17px] md:px-8 lg:px-10">
              {isLoading && (
                <p className="mt-6 text-lime-300/85">Loading lab catalog...</p>
              )}

              {loadError && (
                <div className="mt-6 max-w-3xl rounded-lg border border-rose-800/80 bg-rose-950/40 p-3">
                  <p className="mb-2 text-rose-200">Error: {loadError}</p>
                  <button
                    type="button"
                    className="rounded-md border border-rose-500/70 bg-rose-900/40 px-3 py-1.5 text-sm font-semibold text-rose-100 transition hover:bg-rose-800/50"
                    onClick={() => void refreshLabs()}
                  >
                    Retry
                  </button>
                </div>
              )}

              {!isLoading && !loadError && labs.length === 0 && (
                <div className="mt-6 max-w-3xl rounded-lg border border-lime-700/60 bg-lime-950/25 p-4">
                  <p className="m-0 text-lime-200/85">
                    No launchable labs are currently available.
                  </p>
                </div>
              )}

              {!isLoading && !loadError && modules.length > 0 && (
                <section className="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
                  {modules.map((module) => (
                    // Keep exact visual card set while wiring launchable modules.
                    // Non-launchable modules remain as preview-only placeholders.
                    <ModuleCard
                      key={module.id}
                      module={module}
                      onOpen={
                        module.isLaunchEnabled
                          ? () => {
                              const moduleLab = getModuleLab(module.id, labs);
                              if (moduleLab) {
                                launchLab(moduleLab.id);
                              }
                            }
                          : null
                      }
                    />
                  ))}
                </section>
              )}

              {launchError && (
                <p className="mt-3 text-rose-200">
                  Session launch error: {launchError}
                </p>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default function LabsPage() {
  const bootstrap = useShellBootstrap();
  const navigate = useNavigate();

  return (
    <LabCatalog
      apiBaseUrl={bootstrap.apiBaseUrl}
      learnerLabel={bootstrap.learnerLabel}
      mode={bootstrap.mode}
      onOpenPreLab={(selection) => {
        navigate(`/labs/${selection.labId}/pre-lab`, { state: selection });
      }}
    />
  );
}
