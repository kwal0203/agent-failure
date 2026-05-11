import {
  Shield,
  Box,
  Search,
  ClipboardCheck,
  Users,
  GraduationCap,
  CreditCard,
  Mail,
  Lock,
  Eye,
  Lightbulb,
} from "lucide-react";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50 text-slate-950">
      <div className="mx-auto grid min-h-screen max-w-7xl grid-cols-1 lg:grid-cols-2">
        {/* Left marketing panel */}
        <section className="flex flex-col justify-center px-6 py-10 sm:px-10 lg:px-14">
          <div className="max-w-xl">
            <div className="mb-14 flex items-center gap-5">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-600 shadow-lg shadow-blue-600/20">
                <Shield className="h-9 w-9 text-white" />
              </div>
              <h1 className="text-4xl font-extrabold tracking-tight text-slate-950 sm:text-5xl">
                Agent Failure
              </h1>
            </div>

            <div className="mb-10">
              <p className="mb-3 text-3xl font-extrabold leading-tight tracking-tight text-blue-600 sm:text-4xl">
                AI Agent Security
              </p>
              <p className="text-3xl font-extrabold leading-tight tracking-tight text-blue-600 sm:text-4xl">
                Educational Cyber Range
              </p>
            </div>

            <div className="space-y-6 text-xl leading-8 text-slate-800">
              <p>
                Students learn how AI agents fail by exploiting realistic
                systems in a controlled environment.
              </p>
              <p>
                Attack vulnerable agents, inspect structured traces, and produce
                trace-backed security reports.
              </p>
            </div>

            <div className="mt-14 space-y-10">
              <Feature
                icon={<Box className="h-8 w-8" />}
                title="Sandboxed lab sessions"
                body="Isolated environments for safe, realistic attack scenarios."
              />
              <Feature
                icon={<Search className="h-8 w-8" />}
                title="Trace-grounded feedback"
                body="Detailed, structured traces help students understand exactly what happened."
              />
              <Feature
                icon={<ClipboardCheck className="h-8 w-8" />}
                title="Instructor-ready assessment"
                body="Rubrics, reports, and mapping to standards save instructors time."
              />
            </div>
          </div>
        </section>

        {/* Right login panel */}
        <section className="flex flex-col justify-center px-6 py-10 sm:px-10 lg:px-14">
          <div className="mx-auto w-full max-w-xl">
            <div className="rounded-3xl border border-slate-200 bg-white/90 p-7 shadow-2xl shadow-slate-200/80 backdrop-blur sm:p-10">
              <h2 className="mb-7 text-4xl font-extrabold tracking-tight">
                Sign in
              </h2>

              <p className="mb-7 text-xl text-slate-800">
                Joining or teaching a course?
              </p>

              <div className="space-y-5">
                <ActionCard
                  variant="student"
                  icon={<Users className="h-8 w-8" />}
                  title="Joining a course?"
                  body="Use the class code provided by your instructor."
                  buttonText="Join with class code"
                  buttonIcon={<CreditCard className="h-5 w-5" />}
                  onClick={() => console.log("Join with class code")}
                />

                <ActionCard
                  variant="instructor"
                  icon={<GraduationCap className="h-8 w-8" />}
                  title="Teaching a course?"
                  body="Interested in using Agent Failure in your university course?"
                  buttonText="Request university pilot"
                  buttonIcon={<Users className="h-5 w-5" />}
                  onClick={() => console.log("Request university pilot")}
                />
              </div>

              <Divider label="OR" />

              <form className="space-y-5">
                <div>
                  <label
                    htmlFor="email"
                    className="mb-2 block text-base font-bold text-slate-900"
                  >
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                    <input
                      id="email"
                      type="email"
                      placeholder="you@example.edu"
                      className="h-14 w-full rounded-xl border border-slate-300 bg-white pl-12 pr-4 text-lg text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="password"
                    className="mb-2 block text-base font-bold text-slate-900"
                  >
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                    <input
                      id="password"
                      type="password"
                      placeholder="Enter your password"
                      className="h-14 w-full rounded-xl border border-slate-300 bg-white pl-12 pr-12 text-lg text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                    />
                    <button
                      type="button"
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 transition hover:text-slate-700"
                      aria-label="Show password"
                    >
                      <Eye className="h-5 w-5" />
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  className="h-14 w-full rounded-xl bg-blue-600 text-lg font-bold text-white shadow-lg shadow-blue-600/25 transition hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-200"
                >
                  Sign In
                </button>
              </form>

              <Divider label="Continue with" />

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <OAuthButton icon={<GitHubLogo />} label="GitHub (Soon)" />
                <OAuthButton google label="Google (Soon)" />
              </div>
            </div>

            <div className="mx-auto mt-8 max-w-md space-y-6 text-slate-800">
              <div className="flex gap-4">
                <Lightbulb className="mt-1 h-6 w-6 shrink-0 text-amber-500" />
                <div>
                  <p className="font-bold text-slate-950">Need access?</p>
                  <p className="mt-2 leading-7">
                    Students join with a class code.
                    <br />
                    Instructors can request a university pilot.
                  </p>
                </div>
              </div>

              <div className="space-y-4 text-base">
                <p>
                  Forgot your password?{" "}
                  <a
                    href="/reset-password"
                    className="font-medium text-blue-600 hover:underline"
                  >
                    Reset password
                  </a>
                </p>
                <p>
                  Don&apos;t have an account?{" "}
                  <a
                    href="/signup"
                    className="font-medium text-blue-600 hover:underline"
                  >
                    Create account
                  </a>
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>

      <footer className="border-t border-slate-200 bg-white/60 px-6 py-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 Agent Failure. All rights reserved.</p>
          <div className="flex gap-8">
            <a href="/privacy" className="text-blue-600 hover:underline">
              Privacy Policy
            </a>
            <a href="/terms" className="text-blue-600 hover:underline">
              Terms of Use
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
}

function Feature({ icon, title, body }) {
  return (
    <div className="flex gap-6">
      <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-blue-50 text-blue-600">
        {icon}
      </div>
      <div>
        <h3 className="text-xl font-extrabold text-slate-950">{title}</h3>
        <p className="mt-2 text-lg leading-7 text-slate-700">{body}</p>
      </div>
    </div>
  );
}

function ActionCard({
  variant,
  icon,
  title,
  body,
  buttonText,
  buttonIcon,
  onClick,
}) {
  const isInstructor = variant === "instructor";

  return (
    <div
      className={[
        "rounded-2xl border p-6 transition",
        isInstructor
          ? "border-green-200 bg-green-50/60"
          : "border-blue-200 bg-blue-50/60",
      ].join(" ")}
    >
      <div className="flex flex-col gap-5 sm:flex-row">
        <div
          className={[
            "flex h-16 w-16 shrink-0 items-center justify-center rounded-full",
            isInstructor
              ? "bg-green-100 text-green-600"
              : "bg-blue-100 text-blue-600",
          ].join(" ")}
        >
          {icon}
        </div>

        <div className="flex-1">
          <h3 className="text-xl font-extrabold text-slate-950">{title}</h3>
          <p className="mt-2 text-lg leading-7 text-slate-700">{body}</p>

          <button
            type="button"
            onClick={onClick}
            className={[
              "mt-6 flex h-14 w-full items-center justify-center gap-3 rounded-xl text-lg font-bold text-white shadow-lg transition focus:outline-none focus:ring-4",
              isInstructor
                ? "bg-green-600 shadow-green-600/20 hover:bg-green-700 focus:ring-green-100"
                : "bg-blue-600 shadow-blue-600/20 hover:bg-blue-700 focus:ring-blue-100",
            ].join(" ")}
          >
            {buttonIcon}
            {buttonText}
          </button>
        </div>
      </div>
    </div>
  );
}

function Divider({ label }) {
  return (
    <div className="my-8 flex items-center gap-4">
      <div className="h-px flex-1 bg-slate-200" />
      <span className="text-sm font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </span>
      <div className="h-px flex-1 bg-slate-200" />
    </div>
  );
}

function OAuthButton({ icon, label, google }) {
  return (
    <button
      type="button"
      disabled
      className="flex h-14 items-center justify-center gap-3 rounded-xl border border-slate-300 bg-white text-base font-bold text-slate-900 opacity-80 transition hover:bg-slate-50 disabled:cursor-not-allowed"
    >
      {google ? <GoogleIcon /> : icon}
      {label}
    </button>
  );
}

function GitHubLogo() {
  return (
    <svg viewBox="0 0 24 24" className="h-7 w-7" aria-hidden="true">
      <path
        fill="currentColor"
        d="M12 2C6.48 2 2 6.58 2 12.26c0 4.53 2.87 8.37 6.84 9.73.5.1.68-.22.68-.49 0-.24-.01-.88-.01-1.73-2.78.62-3.37-1.37-3.37-1.37-.45-1.19-1.11-1.5-1.11-1.5-.91-.64.07-.63.07-.63 1 .07 1.53 1.06 1.53 1.06.9 1.57 2.35 1.12 2.92.86.09-.67.35-1.12.63-1.38-2.22-.26-4.56-1.14-4.56-5.08 0-1.12.39-2.04 1.03-2.76-.1-.26-.45-1.31.1-2.72 0 0 .84-.28 2.75 1.05A9.3 9.3 0 0 1 12 6.96c.85 0 1.71.12 2.51.34 1.91-1.33 2.75-1.05 2.75-1.05.55 1.41.2 2.46.1 2.72.64.72 1.03 1.64 1.03 2.76 0 3.95-2.34 4.82-4.57 5.07.36.32.68.95.68 1.92 0 1.38-.01 2.5-.01 2.84 0 .27.18.59.69.49A10.04 10.04 0 0 0 22 12.26C22 6.58 17.52 2 12 2Z"
      />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-7 w-7" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M21.6 12.23c0-.82-.07-1.43-.22-2.06H12v3.76h5.51c-.11.93-.71 2.32-2.05 3.26l-.02.13 2.98 2.31.21.02c1.94-1.79 3.06-4.42 3.06-7.42z"
      />
      <path
        fill="#34A853"
        d="M12 22c2.77 0 5.09-.91 6.79-2.47l-3.23-2.51c-.86.6-2.02 1.02-3.56 1.02-2.72 0-5.03-1.79-5.86-4.26l-.12.01-3.1 2.4-.04.11C4.57 19.7 8.08 22 12 22z"
      />
      <path
        fill="#FBBC05"
        d="M6.14 13.78A6.15 6.15 0 0 1 5.8 12c0-.62.12-1.22.33-1.78l-.01-.13-3.14-2.43-.1.05A9.98 9.98 0 0 0 2 12c0 1.61.39 3.13 1.08 4.47l3.06-2.69z"
      />
      <path
        fill="#EA4335"
        d="M12 5.96c1.93 0 3.23.83 3.97 1.53l2.9-2.83C17.09 3 14.77 2 12 2 8.08 2 4.57 4.3 2.88 7.7l3.25 2.52C6.97 7.75 9.28 5.96 12 5.96z"
      />
    </svg>
  );
}
