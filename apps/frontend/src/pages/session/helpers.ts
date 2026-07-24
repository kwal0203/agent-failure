import type { AgentStatus } from "./types";

export type StatusTone = "danger" | "info" | "neutral" | "success" | "warning";

export function agentStatusTone(status: AgentStatus): StatusTone {
  return status === "active" ? "success" : "neutral";
}

export function objectiveTone(active: boolean): StatusTone {
  return active ? "success" : "info";
}

export function hintTone(
  hasUnread: boolean,
  hasUnlockedAny: boolean,
): StatusTone {
  if (hasUnread) {
    return "warning";
  }
  if (hasUnlockedAny) {
    return "info";
  }
  return "neutral";
}

const STATUS_TONE_CLASSES: Record<StatusTone, string> = {
  danger: "border-rose-800 bg-rose-950/70 text-rose-100",
  info: "border-sky-800 bg-sky-950/70 text-sky-100",
  neutral: "border-slate-600 bg-slate-800/70 text-slate-200",
  success: "border-emerald-800 bg-emerald-950/70 text-emerald-100",
  warning: "border-amber-700 bg-amber-950/70 text-amber-100",
};

export function statusChipClassName(
  tone: StatusTone,
  additionalClasses = "",
): string {
  return [
    "rounded-lg border px-2.5 py-1.5 text-[13px] transition-colors duration-[260ms]",
    STATUS_TONE_CLASSES[tone],
    additionalClasses,
  ]
    .filter(Boolean)
    .join(" ");
}

export function sessionStatusTone(state: string | undefined): StatusTone {
  switch ((state ?? "").toUpperCase()) {
    case "PROVISIONING":
      return "warning";
    case "ACTIVE":
    case "COMPLETED":
      return "success";
    case "FAILED":
    case "ERROR":
      return "danger";
    default:
      return "neutral";
  }
}

export function formatTime(isoTs: string): string {
  const date = new Date(isoTs);
  if (Number.isNaN(date.getTime())) return isoTs;
  return date.toLocaleTimeString();
}

export function jitterDelayMs(
  baseMs: number,
  jitterRatio = 0.15,
  rng: () => number = Math.random,
): number {
  const safeBase = Math.max(0, baseMs);
  const safeRatio = Math.min(1, Math.max(0, jitterRatio));
  const spread = safeBase * safeRatio;
  const offset = (rng() * 2 - 1) * spread;
  return Math.max(0, Math.round(safeBase + offset));
}
