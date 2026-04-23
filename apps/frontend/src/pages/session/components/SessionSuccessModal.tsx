import { formatTime } from "../helpers";

type SessionSuccessModalProps = {
  completedAt: string | null;
  onClose: () => void;
};

export function SessionSuccessModal({
  completedAt,
  onClose,
}: SessionSuccessModalProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Session completion success"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "rgba(3, 11, 19, 0.64)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
      }}
    >
      <section
        style={{
          width: "min(560px, 100%)",
          borderRadius: 16,
          border: "1px solid #3d8f68",
          background:
            "linear-gradient(165deg, rgba(8, 30, 22, 0.98) 0%, rgba(10, 20, 17, 0.98) 100%)",
          boxShadow: "0 16px 40px rgba(0, 0, 0, 0.42)",
          color: "#dcffe9",
          padding: "18px 20px 20px",
          position: "relative",
        }}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Close success popup"
          style={{
            position: "absolute",
            top: 10,
            right: 10,
            width: 30,
            height: 30,
            borderRadius: "50%",
            border: "1px solid #6ba987",
            background: "rgba(12, 38, 28, 0.8)",
            color: "#d9ffe8",
            cursor: "pointer",
            fontSize: 18,
            lineHeight: 1,
          }}
        >
          ×
        </button>
        <div
          aria-hidden="true"
          style={{
            width: 72,
            height: 72,
            borderRadius: "50%",
            margin: "2px auto 12px",
            border: "2px solid #7ee0ad",
            background: "rgba(18, 74, 50, 0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 36,
            fontWeight: 800,
            color: "#b8ffd8",
          }}
        >
          ✓
        </div>
        <h2
          style={{
            margin: "0 0 10px",
            textAlign: "center",
            color: "#dcffe9",
          }}
        >
          Lab completed successfully
        </h2>
        <p style={{ margin: "0 0 8px", textAlign: "center", color: "#c8f6dd" }}>
          All required objectives are complete.
        </p>
        {completedAt ? (
          <p style={{ margin: "0 0 4px", textAlign: "center", opacity: 0.9 }}>
            Completed at {formatTime(completedAt)}
          </p>
        ) : null}
      </section>
    </div>
  );
}
