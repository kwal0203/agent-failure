import { type CSSProperties, type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/context";

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

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError("Email and password are required.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await signup(email, password);
      navigate("/app", { replace: true });
    } catch (error) {
      setError(error instanceof Error ? error.message : "Signup failed.");
    } finally {
      setSubmitting(false);
    }
  };

  const emailError = !email.trim() ? "Email is required." : null;
  const passwordError = !password.trim() ? "Password is required." : null;

  return (
    <main style={pageStyle}>
      <section style={formCardStyle}>
        <p style={{ margin: "0 0 8px", color: "#8ecfe4", letterSpacing: 0.25 }}>
          Agent Failure Platform
        </p>
        <h1 style={{ margin: "0 0 8px", color: "#effcff" }}>Create Account</h1>
        <p style={{ margin: "0 0 14px", color: "#b5dfec" }}>
          Create your account to access labs and session history.
        </p>

        <form
          onSubmit={onSubmit}
          style={{ display: "grid", gap: 10 }}
          noValidate
        >
          <label htmlFor="signup-email">Email</label>
          <input
            id="signup-email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            inputMode="email"
            aria-invalid={emailError ? true : undefined}
            style={inputStyle}
          />

          <label htmlFor="signup-password">Password</label>
          <input
            id="signup-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="new-password"
            aria-invalid={passwordError ? true : undefined}
            style={inputStyle}
          />

          {error ? (
            <p style={{ margin: 0, color: "#ffc4cf", fontSize: 13 }}>{error}</p>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
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
            {submitting ? "Creating account..." : "Create Account"}
          </button>
        </form>
        <p style={{ marginTop: 12, color: "#b5dfec" }}>
          Already have an account? <Link to="/login">Log in</Link>
        </p>
        <p style={{ marginTop: 8, color: "#b5dfec" }}>
          <Link to="/">Back to Home</Link>
        </p>
      </section>
    </main>
  );
}
