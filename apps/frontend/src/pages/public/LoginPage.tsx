import {
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  HelpCircle,
  Shield,
  ShieldCheck,
  User,
  Users,
} from "lucide-react";
import { type ElementType, type ReactNode, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../auth/context";
import { POST_LOGIN_REDIRECT_KEY, resolveSafeNext } from "../../auth/redirect";

function FeatureChip({ children }: { children: ReactNode }) {
  return (
    <div className="flex w-fit items-center gap-3 rounded-xl border border-lime-500/20 bg-black/30 px-4 py-3 text-sm font-semibold text-slate-100 shadow-[0_0_20px_rgba(132,204,22,0.05)] backdrop-blur">
      <CheckCircle2 className="h-5 w-5 text-lime-300" />
      {children}
    </div>
  );
}

type LoginInputProps = {
  label: string;
  placeholder: string;
  type?: "text" | "email" | "password";
  icon: ElementType;
  value: string;
  onChange: (value: string) => void;
  id: string;
  autoComplete?: string;
  active?: boolean;
  rightSlot?: ReactNode;
};

function LoginInput({
  label,
  placeholder,
  type = "text",
  icon: Icon,
  value,
  onChange,
  id,
  autoComplete,
  active = false,
  rightSlot,
}: LoginInputProps) {
  return (
    <label className="block" htmlFor={id}>
      <span className="mb-2 block text-sm font-bold text-slate-100">
        {label}
      </span>

      <div
        className={[
          "flex h-14 items-center rounded-lg border bg-black/40 px-4 transition",
          active
            ? "border-lime-400/80 shadow-[0_0_18px_rgba(132,204,22,0.25)]"
            : "border-slate-600/60 hover:border-lime-400/50",
        ].join(" ")}
      >
        <input
          id={id}
          type={type}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          className="h-full min-w-0 flex-1 bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500"
        />
        {rightSlot ?? <Icon className="h-5 w-5 text-slate-300" />}
      </div>
    </label>
  );
}

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
    <div className="min-h-screen overflow-hidden bg-black text-slate-100">
      <div className="relative min-h-screen">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_25%_30%,rgba(132,204,22,0.15),transparent_30%),radial-gradient(circle_at_80%_45%,rgba(34,197,94,0.14),transparent_28%),linear-gradient(180deg,#020617_0%,#020617_42%,#000_100%)]" />

        <div className="pointer-events-none absolute inset-0 opacity-20">
          <div className="absolute left-0 top-0 h-full w-1/2 bg-[linear-gradient(180deg,rgba(132,204,22,0.25)_1px,transparent_1px)] bg-[size:20px_20px]" />
        </div>

        <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-72 opacity-35">
          <div className="absolute inset-0 bg-[linear-gradient(rgba(132,204,22,0.20)_1px,transparent_1px),linear-gradient(90deg,rgba(132,204,22,0.20)_1px,transparent_1px)] bg-[size:42px_42px] [transform:perspective(600px)_rotateX(62deg)_scale(1.4)] [transform-origin:bottom]" />
          <div className="absolute bottom-16 left-1/2 h-28 w-px -translate-x-1/2 bg-lime-300 shadow-[0_0_40px_rgba(132,204,22,0.9)]" />
        </div>

        <header className="relative z-10 flex items-center justify-end px-6 py-6 md:px-10">
          <div className="flex items-center gap-5 text-sm font-semibold text-slate-300">
            <span className="inline-flex items-center gap-2">
              <HelpCircle className="h-5 w-5" />
              Help
            </span>
            <div className="h-6 w-px bg-lime-500/20" />
            <span className="inline-flex items-center gap-2">
              <ShieldCheck className="h-5 w-5" />
              Status
            </span>
          </div>
        </header>

        <main className="relative z-10 mx-auto grid min-h-[calc(100vh-88px)] max-w-7xl grid-cols-1 items-center gap-12 px-6 pb-12 md:px-10 lg:grid-cols-[1fr_0.95fr]">
          <section className="max-w-2xl">
            <div className="mb-16 flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-lime-500/15 text-lime-300 ring-1 ring-lime-400/40 shadow-[0_0_34px_rgba(132,204,22,0.35)]">
                <Shield className="h-10 w-10" />
              </div>
              <span className="text-3xl font-extrabold tracking-tight text-white">
                Agent Failure
              </span>
            </div>

            <h1 className="text-5xl font-black leading-tight tracking-tight text-white md:text-6xl">
              <span style={{ color: "#ffffff" }}>AI Agent Security</span>
              <span className="block text-lime-300 drop-shadow-[0_0_22px_rgba(132,204,22,0.45)]">
                Educational Cyber Range
              </span>
            </h1>

            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-300">
              Students learn how AI agents fail by exploiting realistic systems
              in a controlled environment.
            </p>
            <br />

            <p className="mt-8 max-w-xl text-lg leading-8 text-slate-300">
              Attack vulnerable agents, inspect structured traces, and produce
              trace-backed security reports.
            </p>

            <div className="mt-8 space-y-4">
              <FeatureChip>Sandboxed lab sessions</FeatureChip>
              <FeatureChip>Trace-grounded feedback</FeatureChip>
              <FeatureChip>Instructor-ready assessment</FeatureChip>
            </div>
          </section>

          <section className="mx-auto w-full max-w-xl rounded-[2rem] border border-lime-400/50 bg-black/45 p-8 shadow-[0_0_46px_rgba(132,204,22,0.18)] backdrop-blur-md md:p-12">
            <div>
              <h2
                className="text-4xl font-black tracking-tight text-white"
                style={{ color: "#ffffff" }}
              >
                Sign in
              </h2>
            </div>

            <div className="mt-6">
              <h3 className="text-lg font-extrabold text-white">
                Joining or teaching a course?
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                Students can join with a class code.
              </p>

              <button
                type="button"
                className="mt-5 flex h-14 w-full items-center justify-center gap-3 rounded-lg border border-lime-400/60 bg-black/30 text-sm font-extrabold text-lime-300 transition hover:bg-lime-500/10 hover:text-lime-200 hover:shadow-[0_0_24px_rgba(132,204,22,0.25)]"
              >
                <Users className="h-5 w-5" />
                Join with class code
              </button>

              <p className="mt-2 text-sm leading-6 text-slate-400">
                Instructors can sign in with their instructor account.
              </p>
              <button
                type="button"
                className="mt-5 flex h-14 w-full items-center justify-center gap-3 rounded-lg border border-lime-400/60 bg-black/30 text-sm font-extrabold text-lime-300 transition hover:bg-lime-500/10 hover:text-lime-200 hover:shadow-[0_0_24px_rgba(132,204,22,0.25)]"
              >
                <Users className="h-5 w-5" />
                Instructor sign in
              </button>
            </div>

            <div className="my-8 flex items-center gap-4">
              <div className="h-px flex-1 bg-lime-500/15" />
              <span className="text-sm font-semibold text-slate-500">OR</span>
              <div className="h-px flex-1 bg-lime-500/15" />
            </div>

            <form
              className="space-y-6"
              onSubmit={(event) => {
                event.preventDefault();
                void onLogin();
              }}
            >
              <LoginInput
                label="Email Address"
                placeholder="you@example.edu"
                icon={User}
                id="login-email"
                type="email"
                value={email}
                onChange={setEmail}
                autoComplete="email"
                active
              />

              <LoginInput
                label="Password"
                placeholder="Enter your password"
                type={showPassword ? "text" : "password"}
                icon={Eye}
                id="login-password"
                value={password}
                onChange={setPassword}
                autoComplete="current-password"
                rightSlot={
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    aria-label={
                      showPassword ? "Hide password" : "Show password"
                    }
                    className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-300 transition hover:bg-lime-500/10 hover:text-lime-200"
                  >
                    {showPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                }
              />

              {submitError ? (
                <p className="text-sm text-rose-300">{submitError}</p>
              ) : null}

              <button
                type="submit"
                disabled={submitting}
                className="group flex h-16 w-full items-center justify-center gap-3 rounded-lg bg-lime-300 text-base font-black text-black shadow-[0_0_28px_rgba(132,204,22,0.55)] transition hover:bg-lime-200 hover:shadow-[0_0_42px_rgba(132,204,22,0.75)] disabled:cursor-not-allowed disabled:opacity-70"
              >
                {submitting ? "Signing In..." : "Sign In"}
                <ArrowRight className="h-5 w-5 transition group-hover:translate-x-1" />
              </button>
            </form>

            <div className="my-8 h-px bg-lime-500/15" />

            <div className="grid gap-3">
              <button
                type="button"
                disabled
                className="h-12 rounded-lg border border-lime-400/40 bg-black/35 text-sm font-bold text-lime-200 opacity-65"
              >
                Continue with GitHub (Soon)
              </button>
              <button
                type="button"
                disabled
                className="h-12 rounded-lg border border-lime-400/40 bg-black/35 text-sm font-bold text-lime-200 opacity-65"
              >
                Continue with Google (Soon)
              </button>
            </div>

            <div className="my-8 h-px bg-lime-500/15" />

            <div className="mt-2 space-y-2 text-sm text-slate-400">
              <p>
                Don&apos;t have an account?{" "}
                <Link
                  to="/signup"
                  className="font-semibold text-lime-300 transition hover:text-lime-200"
                >
                  Create account
                </Link>
              </p>
              <p>
                Forgot your password?{" "}
                <Link
                  to="/forgot-password"
                  className="font-semibold text-lime-300 transition hover:text-lime-200"
                >
                  Reset password
                </Link>
              </p>
            </div>
          </section>
        </main>

        <footer className="relative z-10 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 px-6 pb-8 text-sm text-slate-500">
          <span>© 2026 Agent Failure. All rights reserved.</span>
          <span className="hidden h-4 w-px bg-lime-500/20 sm:block" />
          <span>Privacy Policy</span>
          <span className="hidden h-4 w-px bg-lime-500/20 sm:block" />
          <span>Terms of Use</span>
        </footer>
      </div>
    </div>
  );
}
