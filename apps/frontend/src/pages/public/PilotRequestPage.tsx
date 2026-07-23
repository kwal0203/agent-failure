import { ArrowLeft, ArrowRight, Shield, User } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { createPilotRequest } from "../../auth/pilotRequests";

type PilotInputProps = {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  type?: "text" | "email";
};

function PilotInput({
  id,
  label,
  placeholder,
  value,
  onChange,
  type = "text",
}: PilotInputProps) {
  return (
    <label className="block" htmlFor={id}>
      <span className="mb-2 block text-sm font-bold text-slate-100">
        {label}
      </span>
      <div className="flex h-14 items-center rounded-lg border border-lime-400/80 bg-black/40 px-4 shadow-[0_0_18px_rgba(132,204,22,0.25)] transition">
        <input
          id={id}
          type={type}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          className="h-full min-w-0 flex-1 bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500"
        />
        <User className="h-5 w-5 text-slate-300" />
      </div>
    </label>
  );
}

export default function PilotRequestPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [university, setUniversity] = useState("");
  const [courseName, setCourseName] = useState("");
  const [message, setMessage] = useState("");
  const [website, setWebsite] = useState("");
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async () => {
    if (!name.trim() || !email.trim() || !university.trim()) {
      setError("Name, work email, and university are required.");
      setSuccess(null);
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      await createPilotRequest({
        fullName: name.trim(),
        workEmail: email.trim().toLowerCase(),
        university: university.trim(),
        role: undefined,
        courseName: courseName.trim() || undefined,
        notes: message.trim() || undefined,
        website,
      });
      setSuccess(
        "Request captured. We will follow up to set up your university pilot.",
      );
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Pilot request submission failed.",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen overflow-hidden bg-black text-slate-100">
      <div className="relative min-h-screen">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_25%_30%,rgba(132,204,22,0.15),transparent_30%),radial-gradient(circle_at_80%_45%,rgba(34,197,94,0.14),transparent_28%),linear-gradient(180deg,#020617_0%,#020617_42%,#000_100%)]" />

        <main className="relative z-10 mx-auto grid min-h-screen max-w-7xl grid-cols-1 items-center gap-12 px-6 py-12 md:px-10 lg:grid-cols-[1fr_0.95fr]">
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
              University pilot
              <span className="block text-lime-300 drop-shadow-[0_0_22px_rgba(132,204,22,0.45)]">
                Request access
              </span>
            </h1>
          </section>

          <section className="mx-auto w-full max-w-xl rounded-[2rem] border border-lime-400/50 bg-black/45 p-8 shadow-[0_0_46px_rgba(132,204,22,0.18)] backdrop-blur-md md:p-12">
            <h2 className="mb-7 text-4xl font-extrabold tracking-tight text-white">
              Request university pilot
            </h2>

            <form
              className="space-y-6"
              onSubmit={(event) => {
                event.preventDefault();
                void onSubmit();
              }}
            >
              <label
                className="absolute -left-[10000px] top-auto h-px w-px overflow-hidden"
                htmlFor="pilot-website"
                aria-hidden="true"
              >
                Website
                <input
                  id="pilot-website"
                  name="website"
                  type="text"
                  value={website}
                  onChange={(event) => setWebsite(event.target.value)}
                  autoComplete="off"
                  tabIndex={-1}
                />
              </label>
              <PilotInput
                id="pilot-name"
                label="Full Name"
                placeholder="Your full name"
                value={name}
                onChange={setName}
              />
              <PilotInput
                id="pilot-email"
                label="Work Email"
                placeholder="you@university.edu"
                value={email}
                onChange={setEmail}
                type="email"
              />
              <PilotInput
                id="pilot-university"
                label="University"
                placeholder="University name"
                value={university}
                onChange={setUniversity}
              />
              <PilotInput
                id="pilot-course"
                label="Course (Optional)"
                placeholder="Course title or code"
                value={courseName}
                onChange={setCourseName}
              />

              <label className="block" htmlFor="pilot-message">
                <span className="mb-2 block text-sm font-bold text-slate-100">
                  Notes (Optional)
                </span>
                <textarea
                  id="pilot-message"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="Tell us about your planned cohort and timeline"
                  rows={4}
                  className="w-full rounded-lg border border-lime-400/80 bg-black/40 px-4 py-3 text-sm text-slate-100 shadow-[0_0_18px_rgba(132,204,22,0.25)] outline-none placeholder:text-slate-500"
                />
              </label>

              {success ? (
                <p className="text-sm text-emerald-300">{success}</p>
              ) : null}
              {error ? <p className="text-sm text-rose-300">{error}</p> : null}

              <button
                type="submit"
                disabled={submitting}
                className="group flex h-16 w-full items-center justify-center gap-3 rounded-lg bg-lime-300 text-base font-black text-black shadow-[0_0_28px_rgba(132,204,22,0.55)] transition hover:bg-lime-200 hover:shadow-[0_0_42px_rgba(132,204,22,0.75)]"
              >
                {submitting ? "Submitting..." : "Submit pilot request"}
                <ArrowRight className="h-5 w-5 transition group-hover:translate-x-1" />
              </button>
            </form>

            <div className="my-8 h-px bg-lime-500/15" />

            <Link
              to="/login"
              className="inline-flex items-center gap-2 text-sm font-semibold text-lime-300 transition hover:text-lime-200"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to sign in
            </Link>
          </section>
        </main>
      </div>
    </div>
  );
}
