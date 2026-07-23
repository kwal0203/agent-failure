import {
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  GraduationCap,
  Shield,
  User,
  Users,
} from "lucide-react";
import {
  type ElementType,
  type ReactNode,
  useEffect,
  useRef,
  useState,
} from "react";
import { Link, useNavigate } from "react-router-dom";
import { POST_LOGIN_REDIRECT_KEY } from "../../auth/redirect";
import { useAuth } from "../../auth/useAuth";

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
  const existingAccountRef = useRef<HTMLHeadingElement | null>(null);

  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (window.location.hash !== "#already-have-account") {
      return;
    }
    window.requestAnimationFrame(() => {
      existingAccountRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  }, []);

  const onLogin = async () => {
    if (!email.trim() || !password.trim()) {
      setSubmitError("Email and password are required.");
      return;
    }

    setSubmitError(null);
    setSubmitting(true);
    try {
      window.sessionStorage.setItem(POST_LOGIN_REDIRECT_KEY, "/labs");
      await login(email, password);
      navigate("/labs", { replace: true });
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

        <main className="relative z-10 mx-auto grid min-h-screen max-w-7xl grid-cols-1 items-center gap-12 px-6 pt-8 pb-12 md:px-10 md:pt-10 lg:grid-cols-[1fr_0.95fr]">
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
            <h2
              className="mb-7 text-4xl font-extrabold tracking-tight text-white"
              style={{ color: "#ffffff" }}
            >
              Sign in
            </h2>

            <div className="mt-6">
              <h3 className="text-lg font-extrabold text-white">Get started</h3>
              <div className="mt-4 space-y-4">
                <div className="rounded-xl border border-lime-400/45 bg-black/25 p-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 rounded-lg bg-lime-500/15 p-2 text-lime-300">
                      <Users className="h-5 w-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h4 className="text-sm font-extrabold text-white">
                        Joining a course
                      </h4>
                      <p className="mt-1 text-sm leading-6 text-slate-400">
                        Use the class code provided by your instructor.
                      </p>
                      <Link
                        to="/signup"
                        className="mt-3 inline-flex h-11 items-center justify-center rounded-lg border border-lime-400/60 bg-black/30 px-4 text-sm font-extrabold text-lime-300 transition hover:bg-lime-500/10 hover:text-lime-200"
                      >
                        Join with class code
                      </Link>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-lime-400/45 bg-black/25 p-4">
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 rounded-lg bg-lime-500/15 p-2 text-lime-300">
                      <GraduationCap className="h-5 w-5" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h4 className="text-sm font-extrabold text-white">
                        Teaching a course
                      </h4>
                      <p className="mt-1 text-sm leading-6 text-slate-400">
                        Interested in using Agent Failure in your university
                        course?
                      </p>
                      <button
                        type="button"
                        className="mt-3 inline-flex h-11 items-center justify-center rounded-lg border border-lime-400/60 bg-black/30 px-4 text-sm font-extrabold text-lime-300 transition hover:bg-lime-500/10 hover:text-lime-200"
                        onClick={() => navigate("/pilot-request")}
                      >
                        Request university pilot
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="my-8 flex items-center gap-4">
              <div className="h-px flex-1 bg-lime-500/15" />
              <span className="text-sm font-semibold text-slate-500">OR</span>
              <div className="h-px flex-1 bg-lime-500/15" />
            </div>

            <h3
              id="already-have-account"
              ref={existingAccountRef}
              className="text-lg font-extrabold text-white"
            >
              Already have an account?
            </h3>

            <form
              className="mt-4 space-y-6"
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

            <div className="my-8 flex items-center gap-4">
              <div className="h-px flex-1 bg-lime-500/15" />
              <span className="text-sm font-semibold text-slate-500">
                CONTINUE WITH
              </span>
              <div className="h-px flex-1 bg-lime-500/15" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                disabled
                className="h-12 rounded-lg border border-lime-400/40 bg-black/35 text-sm font-bold text-lime-200 opacity-65"
              >
                GitHub (soon)
              </button>
              <button
                type="button"
                disabled
                className="h-12 rounded-lg border border-lime-400/40 bg-black/35 text-sm font-bold text-lime-200 opacity-65"
              >
                Google (soon)
              </button>
            </div>

            <div className="my-8 h-px bg-lime-500/15" />

            <div className="mt-2 space-y-2 text-sm text-slate-400">
              {/* <p>
                Don&apos;t have an account?{" "}
                <Link
                  to="/signup"
                  className="font-semibold text-lime-300 transition hover:text-lime-200"
                >
                  Create account
                </Link>
              </p> */}
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
          <span>Agent Failure is open-source software.</span>
          <span className="hidden h-4 w-px bg-lime-500/20 sm:block" />
          <Link to="/privacy" className="transition hover:text-lime-300">
            Privacy Policy
          </Link>
          <span className="hidden h-4 w-px bg-lime-500/20 sm:block" />
          <Link to="/terms" className="transition hover:text-lime-300">
            Terms of Use
          </Link>
          <span className="hidden h-4 w-px bg-lime-500/20 sm:block" />
          <Link to="/contact" className="transition hover:text-lime-300">
            Contact
          </Link>
        </footer>
      </div>
    </div>
  );
}
