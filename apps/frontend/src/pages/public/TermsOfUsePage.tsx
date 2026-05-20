import { Link } from "react-router-dom";

export default function TermsOfUsePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0b1220] via-[#111827] to-[#0b1220] px-6 py-12 text-slate-200">
      <main className="mx-auto max-w-3xl rounded-2xl border border-slate-700/60 bg-slate-900/70 p-8 shadow-xl">
        <h1 className="text-3xl font-bold text-lime-300">Terms of Use</h1>
        <p className="mt-6 leading-7 text-slate-200">
          Agent Failure is an educational AI security lab platform only
          available to university students enrolled in verified educational
          courses.
        </p>
        <br />
        <p className="mt-4 leading-7 text-slate-200">
          Users may only use the platform for authorized educational and
          training purposes.
        </p>
        <br />
        <p className="mt-4 leading-7 text-slate-200">
          Users must not attack real systems, misuse the platform, attempt
          unauthorized access, or use the platform for unlawful activity.
        </p>
        <br />
        <p className="mt-4 leading-7 text-slate-200">
          Lab environments are sandboxed for security and all tools are
          simulated. The sandboxes are provided only for controlled learning.
        </p>
        <br />
        <p className="mt-4 leading-7 text-slate-200">
          We may suspend access for misuse.
        </p>
        <br />
        <p className="mt-4 leading-7 text-slate-200">
          Questions can be sent to{" "}
          <a
            className="font-semibold text-lime-300 hover:text-lime-200"
            href="https://www.linkedin.com/in/kanewalter/"
            target="_blank"
            rel="noreferrer"
          >
            Kane Walter
          </a>{" "}
          at{" "}
          <a
            className="font-semibold text-lime-300 hover:text-lime-200"
            href="mailto:kwal0203@gmail.com"
          >
            kwal0203@gmail.com
          </a>
          .
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
