import { formatTime } from "../helpers";
import type { SessionFeedbackItem } from "../types";

type FeedbackPopoverProps = {
  feedbackItems: SessionFeedbackItem[];
};

export function FeedbackPopover({ feedbackItems }: FeedbackPopoverProps) {
  return (
    <section
      className="hints-scroll-region"
      style={{
        position: "absolute",
        top: "calc(100% + 8px)",
        right: 430,
        zIndex: 4,
        width: 420,
        maxWidth: "100%",
        maxHeight: 640,
        overflowY: "auto",
        overflowX: "hidden",
        paddingRight: 6,
        background: "#09131f",
        border: "1px solid #35607f",
        borderRadius: 10,
        padding: 12,
        boxSizing: "border-box",
        boxShadow: "0 10px 24px rgba(0, 0, 0, 0.35)",
      }}
    >
      {feedbackItems.length === 0 ? (
        <p style={{ margin: 0, opacity: 0.88 }}>
          No feedback items yet. Keep interacting to receive coaching feedback.
        </p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {feedbackItems.map((item) => (
            <div
              key={item.id}
              style={{
                border: "1px solid #3e87b3",
                borderRadius: 8,
                padding: 10,
                background: "rgba(17, 61, 89, 0.38)",
              }}
            >
              <p
                style={{
                  margin: "0 0 4px",
                  fontWeight: 700,
                  color: "#d8f1ff",
                  textTransform: "capitalize",
                }}
              >
                {item.severity}
              </p>
              <p style={{ margin: "0 0 6px", color: "#e9f6ff" }}>
                {item.message}
              </p>
              <p style={{ margin: "0 0 4px", fontSize: 12, color: "#cdeeff" }}>
                Reason: {item.reason_code}
              </p>
              <p style={{ margin: 0, fontSize: 12, color: "#cdeeff" }}>
                {formatTime(item.created_at)}
              </p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
