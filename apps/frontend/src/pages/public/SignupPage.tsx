import { type CSSProperties, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/context";

const pageStyle: CSSProperties = {
  minHeight: "100vh",
  padding: "24px",
  boxSizing: "border-box",
  display: "grid",
  placeItems: "center",
  color: "#d7ffd7",
  background: "#040704",
  fontFamily: "'Share Tech Mono', 'Fira Code', 'Courier New', monospace",
};

const formCardStyle: CSSProperties = {
  width: "min(440px, 92vw)",
  border: "1px solid #1b5e20",
  borderRadius: 10,
  padding: 20,
  background: "#0a120a",
};

export default function SignupPage() {
  const { signup, confirmSignup } = useAuth();
  const navigate = useNavigate();

  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmationCode, setConfirmationCode] = useState("");
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);

  const onSignup = async () => {
    if (!email.trim() || !password.trim()) {
      setError("Email and password are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await signup(email, password);
      setAwaitingConfirmation(true);
      setSuccessMessage(
        "Account created. Enter the confirmation code from your email.",
      );
    } catch (error) {
      setError(error instanceof Error ? error.message : "Signup failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const onConfirmSignup = async () => {
    if (!email.trim() || !confirmationCode.trim()) {
      setError("Email and confirmation code are required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setSuccessMessage(null);
    try {
      await confirmSignup(email, confirmationCode);
      setSuccessMessage("Email confirmed. You can now log in.");
      window.setTimeout(() => {
        navigate("/login", { replace: true });
      }, 600);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Confirmation failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main style={pageStyle}>
      <section style={formCardStyle}>
        <h1 style={{ margin: "0 0 8px", color: "#8bff8f", fontSize: 32 }}>
          Create Account
        </h1>
        <div style={{ display: "grid", gap: 10 }}>
          <label htmlFor="signup-email">Email</label>
          <input
            id="signup-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            style={{
              border: "1px solid #2e7d32",
              borderRadius: 6,
              padding: "10px 11px",
              background: "#000",
              color: "#d7ffd7",
            }}
          />
          <label htmlFor="signup-password">Password</label>
          <input
            id="signup-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
            style={{
              border: "1px solid #2e7d32",
              borderRadius: 6,
              padding: "10px 11px",
              background: "#000",
              color: "#d7ffd7",
            }}
          />
          {awaitingConfirmation ? (
            <>
              <label htmlFor="signup-confirm-code">Confirmation Code</label>
              <input
                id="signup-confirm-code"
                value={confirmationCode}
                onChange={(event) => setConfirmationCode(event.target.value)}
                autoComplete="one-time-code"
                style={{
                  border: "1px solid #2e7d32",
                  borderRadius: 6,
                  padding: "10px 11px",
                  background: "#000",
                  color: "#d7ffd7",
                }}
              />
            </>
          ) : null}
          {successMessage ? (
            <p style={{ margin: 0, color: "#9ee8b2", fontSize: 13 }}>
              {successMessage}
            </p>
          ) : null}
          {error ? (
            <p style={{ margin: 0, color: "#ffc4cf", fontSize: 13 }}>{error}</p>
          ) : null}

          <button
            type="button"
            onClick={() =>
              void (awaitingConfirmation ? onConfirmSignup() : onSignup())
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
              : awaitingConfirmation
                ? "Confirm Email"
                : "Create Account with Email"}
          </button>
        </div>
        <p style={{ marginTop: 12, color: "#b6d8b7", fontSize: 13 }}>
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </section>
    </main>
  );
}
