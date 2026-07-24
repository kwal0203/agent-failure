import { useMemo, useState } from "react";
import { useMarkSessionHintsSeenMutation } from "../../../query/sessionMutations";
import type { SessionHint, UnlockedHint } from "../types";

type UseHintsStateParams = {
  sessionId?: string;
  hints?: SessionHint[];
  unreadHintCount?: number;
};

export function useHintsState({
  sessionId,
  hints,
  unreadHintCount,
}: UseHintsStateParams) {
  const [hintsPanelOpen, setHintsPanelOpen] = useState(false);
  const markHintsSeenMutation = useMarkSessionHintsSeenMutation(sessionId);

  const unlockedHints = useMemo<UnlockedHint[]>(() => {
    const unlocked = (hints ?? [])
      .filter((hint) => hint.status === "unlocked")
      .sort((a, b) => {
        const aTime = a.unlocked_at ?? a.unlock_at;
        const bTime = b.unlocked_at ?? b.unlock_at;
        if (aTime !== bTime) {
          return new Date(aTime).getTime() - new Date(bTime).getTime();
        }
        return a.sort_order - b.sort_order;
      });

    return unlocked.map((hint, index) => ({
      index,
      text: hint.text,
      unlockedAt: hint.unlocked_at ?? hint.unlock_at,
    }));
  }, [hints]);
  const hasUnreadHint = (unreadHintCount ?? 0) > 0;

  const onHintsChipClick = () => {
    const nextOpen = !hintsPanelOpen;
    setHintsPanelOpen(nextOpen);
    if (nextOpen && sessionId && hasUnreadHint) {
      markHintsSeenMutation.mutate();
    }
  };

  return { unlockedHints, hintsPanelOpen, hasUnreadHint, onHintsChipClick };
}
