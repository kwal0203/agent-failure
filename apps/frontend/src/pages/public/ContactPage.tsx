import { Link } from "react-router-dom";

export default function ContactPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0b1220] via-[#111827] to-[#0b1220] px-6 py-12 text-slate-200">
      <main className="mx-auto max-w-3xl rounded-2xl border border-slate-700/60 bg-slate-900/70 p-8 shadow-xl">
        <h1 className="text-3xl font-bold text-lime-300">Contact</h1>
        <p className="mt-6 leading-7 text-slate-200">
          For questions about Agent Failure, account access, or course
          participation, contact{" "}
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
