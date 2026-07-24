import { useState } from "react";
import { useMarkSessionFeedbackSeenMutation } from "../../../query/sessionMutations";
import type { SessionFeedbackItem } from "../types";

type UseFeedbackStateParams = {
  sessionId?: string;
  feedbackItems?: SessionFeedbackItem[];
  unreadFeedbackCount?: number;
};

export function useFeedbackState({
  sessionId,
  feedbackItems,
  unreadFeedbackCount,
}: UseFeedbackStateParams) {
  const [feedbackPanelOpen, setFeedbackPanelOpen] = useState(false);
  const markFeedbackSeenMutation =
    useMarkSessionFeedbackSeenMutation(sessionId);
  const hasUnreadFeedback = (unreadFeedbackCount ?? 0) > 0;
  const rows = feedbackItems ?? [];

  const onFeedbackChipClick = () => {
    const nextOpen = !feedbackPanelOpen;
    setFeedbackPanelOpen(nextOpen);
    if (nextOpen && sessionId && hasUnreadFeedback) {
      markFeedbackSeenMutation.mutate();
    }
  };

  return {
    feedbackPanelOpen,
    feedbackItems: rows,
    onFeedbackChipClick,
  };
}
