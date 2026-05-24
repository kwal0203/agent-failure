import type { FormEvent } from "react";

type EmailToolFormProps = {
  emailFrom: string;
  emailSubject: string;
  emailBody: string;
  injectingEmail: boolean;
  sessionId?: string;
  fromValidationError: string | null;
  injectEmailError: string | null;
  injectEmailResult: string | null;
  interactionLocked: boolean;
  onSubmitEmail: (e: FormEvent<HTMLFormElement>) => void;
  onResetEmail: () => void;
  onEmailFromChange: (value: string) => void;
  onEmailSubjectChange: (value: string) => void;
  onEmailBodyChange: (value: string) => void;
};

export function EmailToolForm({
  emailFrom,
  emailSubject,
  emailBody,
  injectingEmail,
  sessionId,
  fromValidationError,
  injectEmailError,
  injectEmailResult,
  interactionLocked,
  onSubmitEmail,
  onResetEmail,
  onEmailFromChange,
  onEmailSubjectChange,
  onEmailBodyChange,
}: EmailToolFormProps) {
  return (
    <form onSubmit={onSubmitEmail} className="space-y-2.5">
      <label className="block text-sm font-semibold text-slate-200">
        <span>From</span>
        <input
          type="email"
          required
          value={emailFrom}
          disabled={interactionLocked}
          onChange={(e) => onEmailFromChange(e.target.value)}
          className="mt-1 w-full rounded-md border border-slate-400/70 bg-black/35 px-3 py-2 text-slate-100 outline-none placeholder:text-slate-500 disabled:cursor-not-allowed disabled:opacity-70"
        />
        {fromValidationError ? (
          <span role="alert" className="mt-1 block text-sm text-rose-300">
            {fromValidationError}
          </span>
        ) : null}
      </label>
      <label className="block text-sm font-semibold text-slate-200">
        <span>Subject</span>
        <input
          type="text"
          required
          value={emailSubject}
          disabled={interactionLocked}
          onChange={(e) => onEmailSubjectChange(e.target.value)}
          className="mt-1 w-full rounded-md border border-slate-400/70 bg-black/35 px-3 py-2 text-slate-100 outline-none placeholder:text-slate-500 disabled:cursor-not-allowed disabled:opacity-70"
        />
      </label>
      <label className="block text-sm font-semibold text-slate-200">
        <span>Body</span>
        <textarea
          rows={4}
          required
          value={emailBody}
          disabled={interactionLocked}
          onChange={(e) => onEmailBodyChange(e.target.value)}
          className="mt-1 w-full resize-y rounded-md border border-slate-400/70 bg-black/35 px-3 py-2 text-slate-100 outline-none placeholder:text-slate-500 disabled:cursor-not-allowed disabled:opacity-70"
        />
      </label>
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={interactionLocked || injectingEmail || !sessionId}
          className={[
            "rounded-lg border px-2.5 py-1.5 text-sm font-semibold transition",
            injectEmailResult
              ? "border-sky-400 bg-sky-900/55 text-sky-100"
              : "border-slate-400 bg-white text-slate-800",
            interactionLocked || injectingEmail || !sessionId
              ? "cursor-not-allowed opacity-70"
              : "cursor-pointer hover:bg-slate-100",
          ].join(" ")}
        >
          {injectingEmail ? "Sending..." : "Send Email"}
        </button>
        <button
          type="button"
          onClick={onResetEmail}
          disabled={interactionLocked || injectingEmail}
          className={[
            "rounded-lg border border-slate-400 bg-white px-2.5 py-1.5 text-sm font-semibold text-slate-800 transition",
            interactionLocked || injectingEmail
              ? "cursor-not-allowed opacity-70"
              : "cursor-pointer hover:bg-slate-100",
          ].join(" ")}
        >
          Reset
        </button>
      </div>
      {injectEmailError && (
        <p className="mt-2 text-sm text-rose-300">{injectEmailError}</p>
      )}
    </form>
  );
}
