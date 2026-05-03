import type { FormEvent } from "react";
import { objectiveTone, statusChipStyle } from "../helpers";

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
  const chipButtonStyle = (active: boolean, disabled: boolean) => ({
    ...statusChipStyle(objectiveTone(active)),
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.7 : 1,
  });

  return (
    <form onSubmit={onSubmitEmail}>
      <label style={{ display: "block", marginBottom: 8 }}>
        From
        <input
          type="email"
          required
          value={emailFrom}
          disabled={interactionLocked}
          onChange={(e) => onEmailFromChange(e.target.value)}
          style={{ width: "100%", marginTop: 4 }}
        />
        {fromValidationError ? (
          <span
            role="alert"
            style={{ display: "block", color: "red", marginTop: 4 }}
          >
            {fromValidationError}
          </span>
        ) : null}
      </label>
      <label style={{ display: "block", marginBottom: 8 }}>
        Subject
        <input
          type="text"
          required
          value={emailSubject}
          disabled={interactionLocked}
          onChange={(e) => onEmailSubjectChange(e.target.value)}
          style={{ width: "100%", marginTop: 4 }}
        />
      </label>
      <label style={{ display: "block", marginBottom: 8 }}>
        Body
        <textarea
          rows={4}
          required
          value={emailBody}
          disabled={interactionLocked}
          onChange={(e) => onEmailBodyChange(e.target.value)}
          style={{ width: "100%", marginTop: 4 }}
        />
      </label>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          type="submit"
          disabled={interactionLocked || injectingEmail || !sessionId}
          style={chipButtonStyle(
            Boolean(injectEmailResult),
            interactionLocked || injectingEmail || !sessionId,
          )}
        >
          {injectingEmail ? "Sending..." : "Send Email"}
        </button>
        <button
          type="button"
          onClick={onResetEmail}
          disabled={interactionLocked || injectingEmail}
          style={chipButtonStyle(false, interactionLocked || injectingEmail)}
        >
          Reset
        </button>
      </div>
      {injectEmailError && (
        <p style={{ color: "red", marginTop: 8 }}>{injectEmailError}</p>
      )}
    </form>
  );
}
