import { Link } from "react-router-dom";

export default function PrivacyPolicyPage() {
  const currentYear = new Date().getFullYear();
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0b1220] via-[#111827] to-[#0b1220] px-6 py-12 text-slate-200">
      <main className="mx-auto max-w-3xl rounded-2xl border border-slate-700/60 bg-slate-900/70 p-8 shadow-xl md:p-10 [&_h2]:pt-2 [&_p]:leading-8">
        <h1 className="text-3xl font-bold text-lime-300">Privacy Policy</h1>
        <p className="mt-3 text-sm text-slate-400">
          Effective date: May 24, 2026. Last updated: May 24, 2026.
        </p>

        <p className="mt-6 leading-7 text-slate-200">
          This Privacy Policy explains how Agent Failure collects, uses, and
          protects personal information when you use our educational AI security
          lab platform.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">
          Information We Collect
        </h2>
        <p className="mt-3 leading-7 text-slate-200">
          We may collect account and profile information (such as email
          address), authentication data (such as login and verification events),
          course and enrollment records, lab participation data, and interaction
          traces generated in the platform.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">
          How We Use Information
        </h2>
        <p className="mt-3 leading-7 text-slate-200">
          We use information to operate and secure the service, manage account
          access, support course participation, evaluate lab progress, provide
          support, and improve platform quality and reliability.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">
          Email Communications
        </h2>
        <p className="mt-3 leading-7 text-slate-200">
          We may send transactional emails for account verification, login
          codes, password reset, and course-related account notifications.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">
          Data Sharing and Sales
        </h2>
        <p className="mt-3 leading-7 text-slate-200">
          We do not sell personal data. We may share information with service
          providers that help us operate the platform, subject to appropriate
          contractual and security controls.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">Data Retention</h2>
        <p className="mt-3 leading-7 text-slate-200">
          We retain data for as long as reasonably necessary to provide the
          service, meet educational and operational needs, resolve disputes, and
          comply with legal obligations.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">Your Choices</h2>
        <p className="mt-3 leading-7 text-slate-200">
          You may request account or data assistance, including deletion
          requests where applicable, by contacting support.
        </p>

        <h2 className="mt-8 text-xl font-bold text-white">Contact</h2>
        <p className="mt-3 leading-7 text-slate-200">
          For privacy questions or deletion requests, contact{" "}
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
