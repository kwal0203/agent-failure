import { Link } from "react-router-dom";

export default function ContactPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0b1220] via-[#111827] to-[#0b1220] px-6 py-12 text-slate-200">
      <main className="mx-auto max-w-3xl rounded-2xl border border-slate-700/60 bg-slate-900/70 p-8 shadow-xl md:p-10 [&_h2]:pt-2 [&_p]:leading-8">
        <h1 className="text-3xl font-bold text-lime-300">Contact</h1>
        <p className="mt-3 text-sm text-slate-400">
          Effective date: May 24, 2026. Last updated: May 24, 2026.
        </p>

        <p className="mt-6 leading-7 text-slate-200">
          For questions about Agent Failure, account access, or course
          participation, contact:
        </p>
        <p className="mt-4 leading-7 text-slate-200">
          <a
            className="font-semibold text-lime-300 hover:text-lime-200"
            href="mailto:support@agentfailure.com"
          >
            support@agentfailure.com
          </a>
          .
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">Support Scope</h2>
        <p className="mt-3 leading-7 text-slate-200">
          This support channel is intended for account access issues, enrollment
          and course participation questions, privacy requests, and platform
          issues.
        </p>

        <div className="mt-8">
          <Link
            to="/login"
            className="text-sm font-semibold text-lime-300 transition hover:text-lime-200"
          >
            Back to Login
          </Link>
        </div>
      </main>
    </div>
  );
}
