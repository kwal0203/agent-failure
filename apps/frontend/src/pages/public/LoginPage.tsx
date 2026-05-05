import { type CSSProperties, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../auth/context";
import { POST_LOGIN_REDIRECT_KEY, resolveSafeNext } from "../../auth/redirect";

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

const shellStyle: CSSProperties = {
  maxWidth: 440,
  margin: "0 auto",
  display: "block",
};

const formCardStyle: CSSProperties = {
  border: "1px solid #1b5e20",
  borderRadius: 10,
  padding: 20,
  background: "#0a120a",
};

const inputStyle: CSSProperties = {
  border: "1px solid #2e7d32",
  borderRadius: 6,
  padding: "10px 11px",
  background: "#000",
  color: "#d7ffd7",
  outline: "none",
};

const ssoButtonStyle: CSSProperties = {
  border: "1px solid #2e7d32",
  background: "#102810",
  color: "#b6ffb9",
  borderRadius: 6,
  padding: "10px 12px",
  fontWeight: 700,
  fontFamily: "inherit",
  fontSize: 16,
  lineHeight: 1.2,
  textAlign: "center",
};

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const next = useMemo(
    () => resolveSafeNext(searchParams.get("next")),
    [searchParams],
  );

  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const onLogin = async () => {
    if (!email.trim() || !password.trim()) {
      setSubmitError("Email and password are required.");
      return;
    }
    setSubmitError(null);
    setSubmitting(true);
    try {
      window.sessionStorage.setItem(POST_LOGIN_REDIRECT_KEY, next);
      await login(email, password);
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
      <section style={shellStyle}>
        <section style={formCardStyle}>
          <h1
            style={{
              margin: "0 0 6px",
              color: "#8bff8f",
              fontSize: 38,
              letterSpacing: 1.1,
            }}
          >
            AgentFailure
          </h1>
          <p style={{ margin: "0 0 16px", color: "#98c89d", fontSize: 13 }}>
            AI Agent Cyber Range
          </p>

          <div style={{ display: "grid", gap: 10 }}>
            <button
              type="button"
              disabled
              style={{ ...ssoButtonStyle, opacity: 0.55 }}
            >
              Continue with GitHub (Soon)
            </button>
            <button
              type="button"
              disabled
              style={{ ...ssoButtonStyle, opacity: 0.55 }}
            >
              Continue with Google (Soon)
            </button>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr auto 1fr",
                alignItems: "center",
                gap: 10,
                margin: "4px 0",
                color: "#7ea683",
                fontSize: 12,
              }}
            >
              <span style={{ height: 1, background: "#224627" }} />
              <span>OR</span>
              <span style={{ height: 1, background: "#224627" }} />
            </div>

            <label htmlFor="login-email">Email Address</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              style={inputStyle}
            />

            <label htmlFor="login-password">Password</label>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr auto",
                alignItems: "center",
                gap: 8,
              }}
            >
              <input
                id="login-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                style={inputStyle}
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                style={{
                  border: "1px solid #2e7d32",
                  borderRadius: 6,
                  background: "#0f1f0f",
                  color: "#b6ffb9",
                  width: 40,
                  height: 40,
                  cursor: "pointer",
                }}
              >
                👁️
              </button>
            </div>

            {submitError ? (
              <p style={{ margin: 0, color: "#ff9ea8", fontSize: 13 }}>
                {submitError}
              </p>
            ) : null}

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr auto",
                gap: 10,
              }}
            >
              <button
                type="button"
                onClick={() => void onLogin()}
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
                {submitting ? "Signing In..." : "Sign In"}
              </button>
              <Link
                to="/forgot-password"
                style={{
                  color: "#a9e8ae",
                  fontSize: 13,
                  alignSelf: "center",
                  textDecoration: "none",
                }}
              >
                Forgot Password?
              </Link>
            </div>

            <p style={{ margin: "4px 0 0", color: "#9dc6a2", fontSize: 13 }}>
              Don&apos;t have an account?{" "}
              <Link to="/signup">Create New Account</Link>
            </p>
          </div>
        </section>
      </section>
    </main>
  );
}
