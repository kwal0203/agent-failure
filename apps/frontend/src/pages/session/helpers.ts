import type { CSSProperties } from "react";
import type { AgentStatus } from "./types";

type StatusTone = {
  background: string;
  border: string;
  color: string;
};

export function agentStatusTone(status: AgentStatus): StatusTone {
  switch (status) {
    case "active":
      return {
        background: "rgba(10, 50, 33, 0.72)",
        border: "1px solid #2e7b57",
        color: "#b9ffe0",
      };
    default:
      return {
        background: "rgba(36, 43, 52, 0.72)",
        border: "1px solid #4a5562",
        color: "#cfd9e2",
      };
  }
}

export function objectiveTone(active: boolean): StatusTone {
  if (active) {
    return {
      background: "rgba(10, 50, 33, 0.72)",
      border: "1px solid #2e7b57",
      color: "#b9ffe0",
    };
  }
  return {
    background: "rgba(8, 31, 50, 0.72)",
    border: "1px solid #285272",
    color: "#9fe4fb",
  };
}

export function hintTone(
  hasUnread: boolean,
  hasUnlockedAny: boolean,
): StatusTone {
  if (hasUnread) {
    return {
      background: "rgba(95, 69, 10, 0.72)",
      border: "1px solid #8f7628",
      color: "#ffe6a6",
    };
  }
  if (hasUnlockedAny) {
    return {
      background: "rgba(8, 31, 50, 0.72)",
      border: "1px solid #285272",
      color: "#9fe4fb",
    };
  }
  return {
    background: "rgba(36, 43, 52, 0.72)",
    border: "1px solid #4a5562",
    color: "#cfd9e2",
  };
}

export function statusChipStyle(tone: StatusTone): CSSProperties {
  return {
    fontSize: 13,
    background: tone.background,
    border: tone.border,
    color: tone.color,
    padding: "6px 10px",
    borderRadius: 8,
    transition:
      "background-color 260ms ease, border-color 260ms ease, color 260ms ease",
  };
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
