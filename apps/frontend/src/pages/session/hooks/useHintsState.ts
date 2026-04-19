import { useEffect, useRef, useState } from "react";
import { HINT_CATALOG, HINT_UNLOCK_SCHEDULE_MS } from "../constants";
import type { TimelineEvent, UnlockedHint } from "../types";

type UseHintsStateParams = {
  sessionId?: string;
  sessionState?: string;
  appendTimelineEvent: (e: TimelineEvent) => void;
};

export function useHintsState({
  sessionId,
  sessionState,
  appendTimelineEvent,
}: UseHintsStateParams) {
  const [unlockedHints, setUnlockedHints] = useState<UnlockedHint[]>([]);
  const [hintsPanelOpen, setHintsPanelOpen] = useState(false);
  const [hasUnreadHint, setHasUnreadHint] = useState(false);
  const hintsStartedAtRef = useRef<number | null>(null);
  const nextHintIndexRef = useRef(0);

  // Reset hint-unlock state whenever the learner switches to a different session.
  useEffect(() => {
    if (!sessionId) return;
    hintsStartedAtRef.current = null;
    nextHintIndexRef.current = 0;
    setUnlockedHints([]);
    setHasUnreadHint(false);
    setHintsPanelOpen(false);
  }, [sessionId]);

  // Start and run the timed hint unlock scheduler while the session is ACTIVE.
  useEffect(() => {
    if ((sessionState ?? "").toUpperCase() !== "ACTIVE") return;
    if (nextHintIndexRef.current >= HINT_CATALOG.length) return;
    if (hintsStartedAtRef.current === null) {
      hintsStartedAtRef.current = Date.now();
    }

    const intervalId = window.setInterval(() => {
      const startedAt = hintsStartedAtRef.current;
      if (startedAt === null) return;

      const elapsedMs = Date.now() - startedAt;
      while (nextHintIndexRef.current < HINT_CATALOG.length) {
        const hintIndex = nextHintIndexRef.current;
        const unlockAtMs =
          HINT_UNLOCK_SCHEDULE_MS[hintIndex] ?? Number.MAX_SAFE_INTEGER;
        if (elapsedMs < unlockAtMs) break;

        const hintText = HINT_CATALOG[hintIndex];
        const unlockedAt = new Date().toISOString();

        setUnlockedHints((prev) => {
          if (prev.some((item) => item.index === hintIndex)) {
            return prev;
          }

          return [
            ...prev,
            {
              index: hintIndex,
              text: hintText,
              unlockedAt,
            },
          ];
        });

        setHasUnreadHint(true);
        appendTimelineEvent({
          id: `hint-unlocked-${hintIndex}-${unlockedAt}`,
          timestamp: unlockedAt,
          type: "explanation",
          granularity: "high",
          title: `Hint ${hintIndex + 1} unlocked`,
          description: "A new hint is available from the Hints chip.",
        });
        nextHintIndexRef.current += 1;
      }
    }, 1000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [appendTimelineEvent, sessionState]);

  const onHintsChipClick = () => {
    setHintsPanelOpen((prev) => !prev);
    setHasUnreadHint(false);
  };

  return { unlockedHints, hintsPanelOpen, hasUnreadHint, onHintsChipClick };
}
