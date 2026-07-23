import { useMemo, useState } from "react";
import type { SessionHint, UnlockedHint } from "../types";
import { API_BASE, getAuthHeader } from "../ui";

type UseHintsStateParams = {
  sessionId?: string;
  hints?: SessionHint[];
  unreadHintCount?: number;
  refreshSessionMetadata: () => Promise<void>;
};

export function useHintsState({
  sessionId,
  hints,
  unreadHintCount,
  refreshSessionMetadata,
}: UseHintsStateParams) {
  const [hintsPanelOpen, setHintsPanelOpen] = useState(false);

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
    setHintsPanelOpen((prev) => {
      const nextOpen = !prev;
      if (nextOpen && sessionId && hasUnreadHint) {
        void (async () => {
          try {
            const res = await fetch(
              `${API_BASE}/api/v1/sessions/${sessionId}/hints/mark-seen`,
              {
                method: "POST",
                headers: {
                  Authorization: await getAuthHeader(),
                  "Content-Type": "application/json",
                },
              },
            );
            if (!res.ok) return;
            await res.json();
            await refreshSessionMetadata();
          } catch {
            return;
          }
        })();
      }
      return nextOpen;
    });
  };

  return { unlockedHints, hintsPanelOpen, hasUnreadHint, onHintsChipClick };
}
