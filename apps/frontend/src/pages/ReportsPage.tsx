import { useQueries } from "@tanstack/react-query";
import {
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
import { useState } from "react";
import { useNavigate } from "react-router";
import { useLabCatalogQuery } from "../query/labCatalog";
import { latestSessionQueryOptions } from "../query/sessionQueries";
import { useShellBootstrap } from "../shell/context";
import type { LabCatalogItem } from "./labCatalogApi";

type CatalogModule = {
  id: string;
  number?: number;
  title: string;
  status: "Pilot Ready" | "Available" | "In Development" | "Planned";
  description: string;
  exerciseCount: number;
  primaryType: "Full Lab" | "Micro-Lab" | "Trace" | "Assessment";
  icon: React.ElementType;
  iconTone: string;
  statusTone: string;
  isReportEnabled: boolean;
};

const EMPTY_LABS: LabCatalogItem[] = [];

const modules: CatalogModule[] = [
  {
    id: "foundations",
    number: 1,
    title: "Foundations of AI Agent Security",
    status: "Planned",
    description: "Agent architecture primer, threat modeling, trace reading",
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
    exerciseCount: 5,
    primaryType: "Full Lab",
    icon: Target,
    iconTone: "bg-yellow-950/70 text-yellow-300 ring-yellow-500/40",
    statusTone: "bg-slate-700/60 text-slate-300 ring-slate-500/30",
    isReportEnabled: false,
  },
];

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

export default function ReportsPage() {
  const bootstrap = useShellBootstrap();
  const navigate = useNavigate();
  const labsQuery = useLabCatalogQuery(bootstrap.apiBaseUrl);
  const labs = labsQuery.data ?? EMPTY_LABS;
  const isLoading = labsQuery.isPending;
  const loadError = labsQuery.error
    ? labsQuery.error instanceof Error
      ? labsQuery.error.message
      : "Failed to load labs"
    : null;
  const [actionError, setActionError] = useState<string | null>(null);
  const latestSessionQueries = useQueries({
    queries: labs.map((lab) =>
      latestSessionQueryOptions(bootstrap.apiBaseUrl, lab.id),
    ),
  });

  return (
    <div className="mx-auto max-w-7xl px-5 pt-5 pb-8 text-[17px] md:px-8 lg:px-10">
      {isLoading ? (
        <p className="mt-6 text-lime-300/85">Loading reports catalog...</p>
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
            const labIndex = moduleLab
              ? labs.findIndex((lab) => lab.id === moduleLab.id)
              : -1;
            const latestSessionId =
              labIndex >= 0 ? latestSessionQueries[labIndex]?.data : undefined;
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
      {/* sidebar/top bar now rendered by AppShell */}
    </div>
  );
}
