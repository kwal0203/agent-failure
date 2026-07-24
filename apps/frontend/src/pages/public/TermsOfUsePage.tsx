import { Link } from "react-router";

export default function TermsOfUsePage() {
  const currentYear = new Date().getFullYear();
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0b1220] via-[#111827] to-[#0b1220] px-6 py-12 text-slate-200">
      <main className="mx-auto max-w-3xl rounded-2xl border border-slate-700/60 bg-slate-900/70 p-8 shadow-xl md:p-10 [&_h2]:pt-2 [&_p]:leading-8">
        <h1 className="text-3xl font-bold text-lime-300">Terms of Use</h1>
        <p className="mt-3 text-sm text-slate-400">
          Effective date: May 24, 2026. Last updated: May 24, 2026.
        </p>

        <p className="mt-6 leading-7 text-slate-200">
          These Terms of Use govern access to and use of Agent Failure. By using
          the platform, you agree to these terms.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">Platform Purpose</h2>
        <p className="mt-3 leading-7 text-slate-200">
          Agent Failure is an educational AI security lab platform intended for
          authorized learning and training use.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">Acceptable Use</h2>
        <p className="mt-3 leading-7 text-slate-200">
          You may use the platform only for authorized educational activities
          and in compliance with applicable laws and institutional policies.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">
          Prohibited Conduct
        </h2>
        <p className="mt-3 leading-7 text-slate-200">
          You must not use the platform to attack real systems, attempt
          unauthorized access, misuse platform resources, or engage in unlawful
          activity.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">
          Lab Environment Notice
        </h2>
        <p className="mt-3 leading-7 text-slate-200">
          Lab environments are intentionally vulnerable and provided only for
          controlled learning within the platform context.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">
          Suspension and Termination
        </h2>
        <p className="mt-3 leading-7 text-slate-200">
          We may suspend or terminate access for policy violations, misuse, or
          security risk.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">
          Disclaimers and Liability
        </h2>
        <p className="mt-3 leading-7 text-slate-200">
          The platform is provided on an "as is" basis for educational use. To
          the maximum extent permitted by law, we disclaim warranties and limit
          liability for indirect or consequential damages.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">Contact</h2>
        <p className="mt-3 leading-7 text-slate-200">
          Questions about these terms can be sent to{" "}
          <a
            className="font-semibold text-lime-300 hover:text-lime-200"
            href="mailto:support@agentfailure.com"
          >
            support@agentfailure.com
          </a>
          .
        </p>

        <div className="mt-8">
          <Link
            to="/login"
            className="inline-flex h-10 items-center justify-center rounded-lg border border-lime-400/50 bg-black/30 px-4 text-sm font-extrabold uppercase tracking-wide text-lime-300 transition hover:bg-lime-500/10 hover:text-lime-200"
          >
            Back
          </Link>
        </div>
      </main>
      <footer className="mx-auto mt-8 max-w-3xl border-t border-lime-800/70 px-1 py-3 text-xs text-lime-200/70">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span>© {currentYear} Agent Failure</span>
          <nav aria-label="Footer links" className="flex flex-wrap gap-3">
            <Link to="/privacy" className="transition hover:text-lime-200">
              Privacy
            </Link>
            <Link to="/terms" className="transition hover:text-lime-200">
              Terms
            </Link>
            <Link to="/contact" className="transition hover:text-lime-200">
              Contact
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
