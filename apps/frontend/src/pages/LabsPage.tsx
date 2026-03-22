import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useShellBootstrap } from "../shell/context";

export default function LabsPage() {
  const bootstrap = useShellBootstrap();
  const navigate = useNavigate();
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const createDemoSession = async () => {
    setIsCreating(true);
    setCreateError(null);

    try {
      const response = await fetch(`${bootstrap.apiBaseUrl}/api/v1/sessions`, {
        method: "POST",
        headers: {
          Authorization: "Bearer local:kane:learner",
          "Idempotency-Key": `frontend-create-session-${crypto.randomUUID()}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          lab_id: crypto.randomUUID(),
        }),
      });

      if (!response.ok) {
        setCreateError(`Session create failed (HTTP ${response.status})`);
        return;
      }

      const payload = (await response.json()) as unknown;
      let sessionId: string | undefined;
      if (
        typeof payload === "object" &&
        payload !== null &&
        "session" in payload &&
        typeof payload.session === "object" &&
        payload.session !== null &&
        "id" in payload.session &&
        typeof payload.session.id === "string"
      ) {
        sessionId = payload.session.id;
      } else if (
        typeof payload === "object" &&
        payload !== null &&
        "id" in payload &&
        typeof payload.id === "string"
      ) {
        sessionId = payload.id;
      }
      if (!sessionId) {
        setCreateError("Session create succeeded but response did not include session id");
        return;
      }

      navigate(`/sessions/${sessionId}`);
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : "Session create failed");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <section>
      <h1 style={{ margin: "0 0 12px" }}>Labs</h1>
      <p style={{ margin: "0 0 14px" }}>
        Demo shell is active for <strong>{bootstrap.learnerLabel}</strong>.
      </p>
      <div
        style={{
          border: "1px solid #cdd5e2",
          borderRadius: 10,
          background: "#fff",
          padding: 16,
          maxWidth: 720,
          margin: "0 auto",
        }}
      >
        <h2 style={{ margin: "0 0 8px", fontSize: 20 }}>Baseline Runtime Lab</h2>
        <p style={{ margin: "0 0 10px" }}>
          Launch and continue a session against the local control-plane runtime path.
        </p>
        <button type="button" onClick={() => void createDemoSession()} disabled={isCreating}>
          {isCreating ? "Creating session..." : "Open demo session"}
        </button>
        {createError && (
          <p style={{ margin: "10px 0 0", color: "#9f1239" }}>
            {createError}
          </p>
        )}
      </div>
    </section>
  );
}
