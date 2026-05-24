import {
  BarChart3,
  Boxes,
  Brain,
  ClipboardCheck,
  ExternalLink,
  ListChecks,
  MessageSquareWarning,
  Network,
  Search,
  Shield,
  Target,
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
  action: "Open Module";
  isLaunchEnabled: boolean;
};

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
