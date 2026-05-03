import { type CSSProperties, type FormEvent, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../auth/context";
import { POST_LOGIN_REDIRECT_KEY, resolveSafeNext } from "../../auth/redirect";

function validateIdentifier(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return "Email is required.";
  if (!/^[^@\s]+@gatech\.edu$/i.test(trimmed)) {
    return "Invalid credentials.";
  }
  return null;
}

function validatePassword(value: string): string | null {
  if (!value.trim()) return "Password is required.";
  return null;
}

const pageStyle: CSSProperties = {
  minHeight: "100vh",
  padding: "32px 20px",
  display: "grid",
  placeItems: "center",
  color: "#d7ffd7",
  background: "#040704",
  fontFamily: "'Share Tech Mono', 'Fira Code', 'Courier New', monospace",
};

const formCardStyle: CSSProperties = {
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

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const next = useMemo(
    () => resolveSafeNext(searchParams.get("next")),
    [searchParams],
  );

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [attemptedSubmit, setAttemptedSubmit] = useState(false);

  const identifierError = attemptedSubmit
    ? validateIdentifier(identifier)
    : null;
  const passwordError = attemptedSubmit ? validatePassword(password) : null;
  const hasFieldErrors = identifierError !== null || passwordError !== null;

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAttemptedSubmit(true);
    setSubmitError(null);

    if (validateIdentifier(identifier) || validatePassword(password)) {
      return;
    }

    setSubmitting(true);
    try {
      window.sessionStorage.setItem(POST_LOGIN_REDIRECT_KEY, next);
      await login(identifier.trim(), password);
      navigate(next, { replace: true });
      window.setTimeout(() => {
        window.sessionStorage.removeItem(POST_LOGIN_REDIRECT_KEY);
      }, 0);
    } catch (error) {
      window.sessionStorage.removeItem(POST_LOGIN_REDIRECT_KEY);
      setSubmitError(
        error instanceof Error
          ? error.message
          : "Login failed. Please try again.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main style={pageStyle}>
      <section style={formCardStyle}>
        <h1
          style={{
            margin: "0 0 16px",
            color: "#8bff8f",
            fontSize: 42,
            letterSpacing: 1.5,
            textShadow: "0 0 10px rgba(139, 255, 143, 0.45)",
            textAlign: "center",
          }}
        >
          AgentFailure
        </h1>

        <form
          onSubmit={onSubmit}
          style={{ display: "grid", gap: 10 }}
          noValidate
        >
          <label htmlFor="login-identifier">Email</label>
          <input
            id="login-identifier"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            autoComplete="email"
            inputMode="email"
            aria-invalid={identifierError ? true : undefined}
            style={inputStyle}
          />
          {identifierError ? (
            <p style={{ margin: 0, color: "#ff9ea8", fontSize: 13 }}>
              {identifierError}
            </p>
          ) : null}

          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            aria-invalid={passwordError ? true : undefined}
            style={inputStyle}
          />
          {passwordError ? (
            <p style={{ margin: 0, color: "#ff9ea8", fontSize: 13 }}>
              {passwordError}
            </p>
          ) : null}

          {submitError ? (
            <p style={{ margin: 0, color: "#ff9ea8", fontSize: 13 }}>
              {submitError}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={submitting || hasFieldErrors}
            style={{
              border: "1px solid #2e7d32",
              background: submitting ? "#1f3321" : "#102810",
              color: "#b6ffb9",
              borderRadius: 6,
              padding: "10px 12px",
              fontWeight: 700,
              cursor: submitting ? "default" : "pointer",
            }}
          >
            {submitting ? "Logging in..." : "Log In"}
          </button>
        </form>
      </section>
    </main>
  );
}
