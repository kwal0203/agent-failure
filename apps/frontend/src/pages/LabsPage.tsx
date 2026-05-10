import {
  BarChart3,
  Bell,
  BookOpen,
  Boxes,
  Brain,
  Bug,
  ClipboardCheck,
  Clock,
  ExternalLink,
  Eye,
  FileText,
  GraduationCap,
  Home,
  Info,
  Landmark,
  LifeBuoy,
  ListChecks,
  Lock,
  MessageSquareWarning,
  Network,
  Search,
  Shield,
  Target,
  Users,
  Wrench,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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
  action: "Open Module" | "Preview";
};

const navItems = [
  { label: "Dashboard", icon: Home },
  { label: "Catalog", icon: BookOpen, active: true },
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
    action: "Preview",
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
    action: "Preview",
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
    action: "Preview",
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
    action: "Preview",
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
    action: "Preview",
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

function FilterChip({
  children,
  active = false,
}: {
  children: React.ReactNode;
  active?: boolean;
}) {
  return (
    <button
      className={[
        "inline-flex items-center justify-center rounded-lg border px-5 py-2 text-sm font-bold transition",
        active
          ? "border-lime-400/80 bg-lime-500/10 text-lime-200 shadow-[0_0_20px_rgba(132,204,22,0.25)]"
          : "border-emerald-500/20 bg-slate-950/70 text-slate-200 hover:border-lime-400/60 hover:bg-lime-500/10 hover:text-lime-200",
      ].join(" ")}
      type="button"
    >
      {children}
    </button>
  );
}

function StandardChip({
  icon: Icon,
  label,
  accent = "text-lime-300",
}: {
  icon: React.ElementType;
  label: string;
  accent?: string;
}) {
  return (
    <button
      type="button"
      className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/20 bg-slate-950/70 px-4 py-2 text-sm font-bold text-slate-200 transition hover:border-lime-400/60 hover:bg-lime-500/10 hover:text-lime-100"
    >
      <Icon className={`h-4 w-4 ${accent}`} />
      {label}
    </button>
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
  const isOpen = module.action === "Open Module";

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
        disabled={!onOpen}
        className={[
          "mt-4 inline-flex h-10 items-center justify-center gap-2 rounded-lg border text-sm font-extrabold transition",
          isOpen
            ? "border-lime-400/70 bg-lime-500/10 text-lime-200 hover:bg-lime-400/15 hover:shadow-[0_0_22px_rgba(132,204,22,0.25)]"
            : "border-lime-500/35 bg-slate-950/60 text-lime-300 hover:border-lime-400/70 hover:bg-lime-500/10",
          onOpen ? "" : "cursor-not-allowed opacity-75",
        ].join(" ")}
      >
        {module.action}
        {isOpen ? (
          <ExternalLink className="h-4 w-4" />
        ) : (
          <Eye className="h-4 w-4" />
        )}
      </button>
    </article>
  );
}

function Sidebar() {
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
              className={[
                "relative flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold transition",
                item.active
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

function FeaturedPilotModule({ onOpen }: { onOpen: () => void }) {
  return (
    <section className="relative overflow-hidden rounded-2xl border border-lime-400/40 bg-slate-950/70 p-6 shadow-[0_0_35px_rgba(132,204,22,0.12)] backdrop-blur">
      <div className="pointer-events-none absolute inset-0 opacity-30">
        <div className="absolute inset-x-0 bottom-0 h-32 bg-[linear-gradient(rgba(132,204,22,0.15)_1px,transparent_1px),linear-gradient(90deg,rgba(132,204,22,0.15)_1px,transparent_1px)] bg-[size:36px_36px]" />
        <div className="absolute right-0 top-0 h-full w-1/2 bg-[radial-gradient(circle_at_top_right,rgba(132,204,22,0.22),transparent_45%)]" />
      </div>

      <div className="relative mb-4 flex items-center gap-2 text-xs font-extrabold uppercase tracking-wide text-lime-300">
        <Target className="h-4 w-4 fill-lime-300 text-lime-300" />
        Recommended Pilot Module
      </div>

      <div className="relative grid gap-6 lg:grid-cols-[1.4fr_1fr_auto] lg:items-center">
        <div className="flex gap-5">
          <div className="hidden h-28 w-28 shrink-0 items-center justify-center rounded-full bg-lime-500/10 text-lime-300 ring-1 ring-lime-400/50 shadow-[0_0_30px_rgba(132,204,22,0.22)] sm:flex">
            <div className="relative">
              <MessageSquareWarning className="h-14 w-14" />
              <div className="absolute -right-2 -bottom-2 flex h-8 w-8 items-center justify-center rounded-full bg-lime-400 text-slate-950 shadow-[0_0_18px_rgba(132,204,22,0.7)]">
                <Lock className="h-4 w-4" />
              </div>
            </div>
          </div>

          <div>
            <h2 className="text-2xl font-extrabold tracking-tight text-slate-100">
              Prompt Injection & Goal Hijacking
            </h2>

            <div className="mt-4 space-y-3 text-sm text-slate-300">
              <StatusBadge
                label="Pilot Ready"
                className="bg-lime-500/15 text-lime-300 ring-lime-400/30"
              />

              <div className="flex items-center gap-3">
                <Users className="h-4 w-4 text-lime-300/80" />
                <span>
                  <span className="font-semibold text-slate-200">
                    Includes:
                  </span>{" "}
                  OpsMail Assistant
                </span>
              </div>

              <div className="flex items-center gap-3">
                <Clock className="h-4 w-4 text-lime-300/80" />
                <span>
                  <span className="font-semibold text-slate-200">Time:</span>{" "}
                  45–75 min including briefing/report
                </span>
              </div>

              <div className="flex items-center gap-3">
                <FileText className="h-4 w-4 text-lime-300/80" />
                <span>
                  <span className="font-semibold text-slate-200">
                    Assessment:
                  </span>{" "}
                  Trace-backed lab report
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-lime-500/20 pt-5 lg:border-t-0 lg:border-l lg:pt-0 lg:pl-6">
          <h3 className="mb-4 text-sm font-extrabold text-slate-100">
            What&apos;s Included
          </h3>

          <ol className="space-y-3 text-sm text-slate-300">
            {[
              "Full Lab: OpsMail Assistant",
              "Trace Exercise",
              "Defense Exercise",
              "Report",
            ].map((item, index) => (
              <li key={item} className="flex items-center gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-lime-500/20 text-xs font-extrabold text-lime-200 ring-1 ring-lime-400/40">
                  {index + 1}
                </span>
                {item}
              </li>
            ))}
          </ol>
        </div>

        <button
          type="button"
          onClick={onOpen}
          className="inline-flex h-12 items-center justify-center gap-2 rounded-xl border border-lime-300/80 bg-lime-500/10 px-6 text-sm font-extrabold text-lime-100 shadow-[0_0_24px_rgba(132,204,22,0.35)] transition hover:bg-lime-400/20 hover:shadow-[0_0_34px_rgba(132,204,22,0.55)]"
        >
          Open Module
          <ExternalLink className="h-4 w-4" />
        </button>
      </div>
    </section>
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
    root.style.fontSize = "16px";
    return () => {
      root.style.fontSize = previousFontSize;
    };
  }, [mode]);

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

  const pilotModule = getModuleLab("foundations", labs);

  return (
    <div className="min-h-screen bg-black font-sans text-slate-100 antialiased">
      <div className="relative flex min-h-screen overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(132,204,22,0.12),transparent_30%),radial-gradient(circle_at_top_right,rgba(34,197,94,0.10),transparent_28%),linear-gradient(180deg,#020617_0%,#020617_40%,#000_100%)]" />

        <div className="pointer-events-none absolute top-0 right-8 hidden h-80 w-96 opacity-20 lg:block">
          <div className="h-full w-full bg-[linear-gradient(180deg,rgba(132,204,22,0.35)_1px,transparent_1px)] bg-[size:18px_18px]" />
        </div>

        <Sidebar />

        <main className="relative min-w-0 flex-1">
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

                <div className="flex items-center gap-2 pl-1">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-800 text-xs font-extrabold text-slate-100 ring-1 ring-lime-500/20">
                    IN
                  </div>
                  <span className="hidden text-sm font-semibold text-slate-300 sm:inline">
                    Instructor
                  </span>
                </div>
              </div>
            </div>
          </header>

          <div className="mx-auto max-w-7xl px-5 pt-5 pb-8 md:px-8 lg:px-10">
            <section className="mb-6 space-y-4">
              <div className="flex flex-wrap gap-3">
                <FilterChip active>All</FilterChip>
                <FilterChip>Full Labs</FilterChip>
                <FilterChip>Micro-Labs</FilterChip>
                <FilterChip>Trace Exercises</FilterChip>
                <FilterChip>Assessments</FilterChip>
              </div>

              <div className="flex flex-wrap gap-3">
                <StandardChip icon={Bug} label="OWASP Agentic" />
                <StandardChip
                  icon={Brain}
                  label="OWASP LLM"
                  accent="text-fuchsia-300"
                />
                <StandardChip icon={Network} label="MITRE ATLAS" />
                <StandardChip icon={Landmark} label="NIST AI RMF" />
              </div>
            </section>

            {pilotModule && (
              <FeaturedPilotModule onOpen={() => launchLab(pilotModule.id)} />
            )}

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
                      module.action === "Open Module"
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

            <div className="mt-6 flex items-center justify-center gap-2 text-sm text-slate-400">
              <Info className="h-4 w-4 text-lime-300" />
              <p>
                Modules group related labs, exercises, and assessments by topic.
                Open a module to see all included activities.
              </p>
            </div>

            {launchError && (
              <p className="mt-3 text-rose-200">
                Session launch error: {launchError}
              </p>
            )}
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
