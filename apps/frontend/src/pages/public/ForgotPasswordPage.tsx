import { type CSSProperties, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/context";

const pageStyle: CSSProperties = {
  minHeight: "100vh",
  padding: "32px 20px",
  display: "grid",
  placeItems: "center",
  color: "#d7ffd7",
  background: "#040704",
  fontFamily: "'Share Tech Mono', 'Fira Code', 'Courier New', monospace",
};

const cardStyle: CSSProperties = {
  width: "min(420px, 92vw)",
  border: "1px solid #1b5e20",
  borderRadius: 8,
  padding: 20,
  background: "#0a120a",
};

const inputStyle: CSSProperties = {
  border: "1px solid #2e7d32",
  borderRadius: 6,
  padding: "10px 11px",
  background: "#000",
  color: "#d7ffd7",
};

export default function ForgotPasswordPage() {
  const { requestPasswordReset, confirmPasswordReset } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [step, setStep] = useState<"request" | "confirm">("request");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const onRequest = async () => {
    if (!email.trim()) {
      setError("Email is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      await requestPasswordReset(email);
      setStep("confirm");
      setMessage("Reset code sent. Check your email.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reset request failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const onConfirm = async () => {
    if (!email.trim() || !code.trim() || !newPassword.trim()) {
      setError("Email, code, and new password are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setMessage(null);
    try {
      await confirmPasswordReset(email, code, newPassword);
      setMessage("Password updated. Redirecting to login.");
      window.setTimeout(() => navigate("/login", { replace: true }), 700);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Password reset failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main style={pageStyle}>
      <section style={cardStyle}>
        <h1 style={{ margin: "0 0 12px", color: "#8bff8f", fontSize: 30 }}>
          Reset Password
        </h1>
        <div style={{ display: "grid", gap: 10 }}>
          <label htmlFor="reset-email">Email</label>
          <input
            id="reset-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            style={inputStyle}
            autoComplete="email"
          />

          {step === "confirm" ? (
            <>
              <label htmlFor="reset-code">Verification Code</label>
              <input
                id="reset-code"
                value={code}
                onChange={(event) => setCode(event.target.value)}
                style={inputStyle}
                autoComplete="one-time-code"
              />
              <label htmlFor="reset-password">New Password</label>
              <input
                id="reset-password"
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                style={inputStyle}
                autoComplete="new-password"
              />
            </>
          ) : null}

          {message ? (
            <p style={{ margin: 0, color: "#9ee8b2", fontSize: 13 }}>
              {message}
            </p>
          ) : null}
          {error ? (
            <p style={{ margin: 0, color: "#ff9ea8", fontSize: 13 }}>{error}</p>
          ) : null}

          <button
            type="button"
            onClick={() =>
              void (step === "request" ? onRequest() : onConfirm())
            }
            disabled={submitting}
            style={{
              fontFamily: "inherit",
              fontSize: 16,
              lineHeight: 1.2,
              border: "1px solid #2e7d32",
              background: submitting ? "#1f3321" : "#102810",
              color: "#b6ffb9",
              borderRadius: 6,
              padding: "10px 12px",
              fontWeight: 700,
              cursor: submitting ? "default" : "pointer",
            }}
          >
            {submitting
              ? "Submitting..."
              : step === "request"
                ? "Send Reset Code"
                : "Update Password"}
          </button>

          <p style={{ margin: "4px 0 0", fontSize: 13 }}>
            <Link to="/login">Back to login</Link>
          </p>
        </div>
      </section>
    </main>
  );
}
