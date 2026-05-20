import { Link } from "react-router-dom";

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0b1220] via-[#111827] to-[#0b1220] px-6 py-12 text-slate-200">
      <main className="mx-auto max-w-3xl rounded-2xl border border-slate-700/60 bg-slate-900/70 p-8 shadow-xl">
        <h1 className="text-3xl font-bold text-lime-300">Privacy Policy</h1>
        <p className="mt-6 leading-7 text-slate-200">
          Agent Failure collects account information such as email address,
          login/authentication data, course/lab participation records, and
          security-lab interaction traces.
        </p>
        <br />
        <p className="mt-4 leading-7 text-slate-200">
          We use this information to provide the service, manage account access,
          support course participation, evaluate lab progress, and improve the
          platform.
        </p>
        <p className="mt-4 leading-7 text-slate-200">
          We do not sell personal data.
        </p>
        <br />
        <p className="mt-4 leading-7 text-slate-200">
          Transactional emails may be sent for account verification, login
          codes, password reset, and course-related account notifications.
        </p>
        <br />
        <p className="mt-4 leading-7 text-slate-200">
          Users can contact{" "}
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
          </a>{" "}
          for privacy questions or deletion requests.
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
