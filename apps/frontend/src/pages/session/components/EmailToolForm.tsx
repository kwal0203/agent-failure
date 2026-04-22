import type { FormEvent } from "react";
import { objectiveTone, statusChipStyle } from "../helpers";

type EmailToolFormProps = {
  emailFrom: string;
  emailSubject: string;
  emailBody: string;
  emailMalicious: boolean;
  injectingEmail: boolean;
  sessionId?: string;
  injectEmailError: string | null;
  injectEmailResult: string | null;
  onSubmitEmail: (e: FormEvent<HTMLFormElement>) => void;
  onResetEmail: () => void;
  onEmailFromChange: (value: string) => void;
  onEmailSubjectChange: (value: string) => void;
  onEmailBodyChange: (value: string) => void;
  onEmailMaliciousChange: (value: boolean) => void;
};

export function EmailToolForm({
  emailFrom,
  emailSubject,
  emailBody,
  emailMalicious,
  injectingEmail,
  sessionId,
  injectEmailError,
  injectEmailResult,
  onSubmitEmail,
  onResetEmail,
  onEmailFromChange,
  onEmailSubjectChange,
  onEmailBodyChange,
  onEmailMaliciousChange,
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
          type="text"
          value={emailFrom}
          onChange={(e) => onEmailFromChange(e.target.value)}
          style={{ width: "100%", marginTop: 4 }}
        />
      </label>
      <label style={{ display: "block", marginBottom: 8 }}>
        Subject
        <input
          type="text"
          value={emailSubject}
          onChange={(e) => onEmailSubjectChange(e.target.value)}
          style={{ width: "100%", marginTop: 4 }}
        />
      </label>
      <label style={{ display: "block", marginBottom: 8 }}>
        Body
        <textarea
          rows={4}
          value={emailBody}
          onChange={(e) => onEmailBodyChange(e.target.value)}
          style={{ width: "100%", marginTop: 4 }}
        />
      </label>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          type="button"
          onClick={() => onEmailMaliciousChange(!emailMalicious)}
          aria-pressed={emailMalicious}
          disabled={injectingEmail}
          title="Toggle malicious flag"
          style={chipButtonStyle(emailMalicious, injectingEmail)}
        >
          {emailMalicious ? "Malicious: On" : "Malicious: Off"}
        </button>
        <button
          type="submit"
          disabled={injectingEmail || !sessionId}
          style={chipButtonStyle(
            Boolean(injectEmailResult),
            injectingEmail || !sessionId,
          )}
        >
          {injectingEmail ? "Injecting..." : "Send Email"}
        </button>
        <button
          type="button"
          onClick={onResetEmail}
          disabled={injectingEmail}
          style={chipButtonStyle(false, injectingEmail)}
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
