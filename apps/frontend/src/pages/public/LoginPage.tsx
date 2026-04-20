import { type CSSProperties, type FormEvent, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../auth/context";
import { POST_LOGIN_REDIRECT_KEY, resolveSafeNext } from "../../auth/redirect";

function validateIdentifier(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return "Email or username is required.";
  if (trimmed.length < 3)
    return "Email or username must be at least 3 characters.";
  return null;
}

function validatePassword(value: string): string | null {
  if (!value.trim()) return "Password is required.";
  return null;
}

const pageStyle: CSSProperties = {
  minHeight: "100vh",
  padding: "32px 20px",
  color: "#d7f5ff",
  background:
    "radial-gradient(900px 560px at 10% -4%, rgba(0, 230, 255, 0.16), transparent 52%), radial-gradient(700px 440px at 92% -4%, rgba(28, 160, 255, 0.18), transparent 52%), linear-gradient(180deg, #040b14 0%, #071321 52%, #081726 100%)",
};

const formCardStyle: CSSProperties = {
  maxWidth: 480,
  margin: "0 auto",
  border: "1px solid #1f4564",
  borderRadius: 14,
  padding: 16,
  background: "rgba(8, 27, 45, 0.78)",
  backdropFilter: "blur(5px)",
};

const inputStyle: CSSProperties = {
  border: "1px solid #2d5e80",
  borderRadius: 8,
  padding: "10px 11px",
  background: "#0a2236",
  color: "#e9fbff",
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
        <p style={{ margin: "0 0 8px", color: "#8ecfe4", letterSpacing: 0.25 }}>
          Agent Failure Platform
        </p>
        <h1 style={{ margin: "0 0 8px", color: "#effcff" }}>Log In</h1>
        <p style={{ margin: "0 0 14px", color: "#b5dfec" }}>
          Enter your credentials to continue to the platform.
        </p>

        <form
          onSubmit={onSubmit}
          style={{ display: "grid", gap: 10 }}
          noValidate
        >
          <label htmlFor="login-identifier">Email or Username</label>
          <input
            id="login-identifier"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            autoComplete="username"
            inputMode="text"
            aria-invalid={identifierError ? true : undefined}
            style={inputStyle}
          />
          {identifierError ? (
            <p style={{ margin: 0, color: "#ffc4cf", fontSize: 13 }}>
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
            <p style={{ margin: 0, color: "#ffc4cf", fontSize: 13 }}>
              {passwordError}
            </p>
          ) : null}

          {submitError ? (
            <p style={{ margin: 0, color: "#ffc4cf", fontSize: 13 }}>
              {submitError}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={submitting || hasFieldErrors}
            style={{
              border: "1px solid #2b6f98",
              background: submitting ? "#24445b" : "#0f3b5d",
              color: "#dcf9ff",
              borderRadius: 9,
              padding: "10px 12px",
              fontWeight: 700,
              cursor: submitting ? "default" : "pointer",
            }}
          >
            {submitting ? "Logging in..." : "Log In"}
          </button>
        </form>

        <p style={{ marginTop: 12, color: "#b5dfec" }}>
          Need an account? <Link to="/signup">Sign up</Link>
        </p>
        <p style={{ marginTop: 8, color: "#b5dfec" }}>
          <Link to="/">Back to Home</Link>
        </p>
      </section>
    </main>
  );
}
