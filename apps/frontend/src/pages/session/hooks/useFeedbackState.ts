import { useState } from "react";
import type { SessionFeedbackItem } from "../types";
import { API_BASE, AUTH_HEADER } from "../ui";

type UseFeedbackStateParams = {
  sessionId?: string;
  feedbackItems?: SessionFeedbackItem[];
  unreadFeedbackCount?: number;
  refreshSessionMetadata: () => Promise<void>;
};

export function useFeedbackState({
  sessionId,
  feedbackItems,
  unreadFeedbackCount,
  refreshSessionMetadata,
}: UseFeedbackStateParams) {
  const [feedbackPanelOpen, setFeedbackPanelOpen] = useState(false);
  const hasUnreadFeedback = (unreadFeedbackCount ?? 0) > 0;
  const rows = feedbackItems ?? [];

  const onFeedbackChipClick = () => {
    setFeedbackPanelOpen((prev) => {
      const nextOpen = !prev;
      if (nextOpen && sessionId && hasUnreadFeedback) {
        void (async () => {
          try {
            const res = await fetch(
              `${API_BASE}/api/v1/sessions/${sessionId}/feedback/mark-seen`,
              {
                method: "POST",
                headers: {
                  Authorization: AUTH_HEADER,
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

  return {
    feedbackPanelOpen,
    feedbackItems: rows,
    onFeedbackChipClick,
  };
}
