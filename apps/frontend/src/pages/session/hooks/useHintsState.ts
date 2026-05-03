import { useEffect, useMemo, useRef, useState } from "react";
import type { SessionHint, TimelineEvent, UnlockedHint } from "../types";
import { API_BASE, getAuthHeader } from "../ui";

type UseHintsStateParams = {
  sessionId?: string;
  hints?: SessionHint[];
  unreadHintCount?: number;
  refreshSessionMetadata: () => Promise<void>;
  appendTimelineEvent: (event: TimelineEvent) => void;
};

export function useHintsState({
  sessionId,
  hints,
  unreadHintCount,
  refreshSessionMetadata,
  appendTimelineEvent,
}: UseHintsStateParams) {
  const [hintsPanelOpen, setHintsPanelOpen] = useState(false);
  const seenHintTimelineEventIdsRef = useRef(new Set<string>());

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

  useEffect(() => {
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

    for (const hint of unlocked) {
      const unlockedAt = hint.unlocked_at ?? hint.unlock_at;
      const eventId = `hint-unlocked-${hint.hint_key}-${unlockedAt}`;
      if (seenHintTimelineEventIdsRef.current.has(eventId)) continue;
      seenHintTimelineEventIdsRef.current.add(eventId);

      appendTimelineEvent({
        id: eventId,
        timestamp: unlockedAt,
        type: "system",
        granularity: "high",
        title: `Hint ${hint.sort_order + 1} unlocked`,
        description: "A new hint is available.",
        details: hint.text,
      });
    }
  }, [hints, appendTimelineEvent]);

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
                  Authorization: getAuthHeader(),
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
