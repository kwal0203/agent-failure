import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useEffect, useRef, useState } from "react";
import type {
  AgentStatus,
  InjectSessionEmailResponse,
  SessionWorkspaceState,
  TimelineEvent,
  ToolKey,
  TranscriptEntry,
} from "../types";
import { API_BASE, AUTH_HEADER } from "../ui";

type UseSessionActionsParams = {
  sessionId?: string;
  canSend: boolean;
  sendPrompt: (text: string) => void;
  setTranscriptEntries: Dispatch<SetStateAction<TranscriptEntry[]>>;
  setIsAwaitingResponse: Dispatch<SetStateAction<boolean>>;
  resetActiveStream: () => void;
  setAgentStatus: (status: AgentStatus) => void;
  appendTimelineEvent: (event: TimelineEvent) => void;
  refreshSessionMetadata: () => Promise<void>;
};

export function useSessionActions(params: UseSessionActionsParams) {
  const injectSuccessTimeoutRef = useRef<number | null>(null);
  const [prompt, setPrompt] = useState("");
  const [emailFrom, setEmailFrom] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");
  const [emailMalicious, setEmailMalicious] = useState(true);
  const [injectingEmail, setInjectingEmail] = useState(false);
  const [injectEmailError, setInjectEmailError] = useState<string | null>(null);
  const [injectEmailResult, setInjectEmailResult] = useState<string | null>(
    null,
  );
  const [workspaceState, setWorkspaceState] = useState<SessionWorkspaceState>({
    selectedTool: null,
    toolPaneOpen: false,
  });

  const onSubmitPrompt = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!params.canSend) return;
    const text = prompt.trim();
    if (!text) return;

    params.setTranscriptEntries((entries) => [
      ...entries,
      { role: "user", content: text, timestamp: new Date().toISOString() },
    ]);
    params.resetActiveStream();
    params.setIsAwaitingResponse(true);
    params.setAgentStatus("active");
    params.sendPrompt(text);
    setPrompt("");
  };

  const onSubmitEmail = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!params.sessionId) return;

    const sender = emailFrom.trim();
    const subject = emailSubject.trim();
    const body = emailBody.trim();
    if (!sender || !subject || !body) {
      setInjectEmailError("From, subject, and body are required.");
      return;
    }

    setInjectingEmail(true);
    setInjectEmailError(null);
    if (injectSuccessTimeoutRef.current !== null) {
      window.clearTimeout(injectSuccessTimeoutRef.current);
      injectSuccessTimeoutRef.current = null;
    }
    setInjectEmailResult(null);

    try {
      const res = await fetch(
        `${API_BASE}/api/v1/sessions/${params.sessionId}/inbox/email`,
        {
          method: "POST",
          headers: {
            Authorization: AUTH_HEADER,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email_from: sender,
            email_subject: subject,
            email_body: body,
            malicious: emailMalicious,
            source: "learner",
          }),
        },
      );

      const payload = (await res.json()) as
        | InjectSessionEmailResponse
        | { error?: { message?: string } };

      if (!res.ok) {
        const msg =
          "error" in payload && payload.error?.message
            ? payload.error.message
            : `HTTP ${res.status}`;
        setInjectEmailError(msg);
        params.appendTimelineEvent({
          id: `email-inject-error-${new Date().toISOString()}-${res.status}`,
          timestamp: new Date().toISOString(),
          type: "system",
          granularity: "high",
          title: "Email injection failed",
          description: msg,
          important: true,
        });
        return;
      }

      const accepted =
        "accepted" in payload && payload.accepted ? "accepted" : "submitted";
      const emailId =
        "email_id" in payload && payload.email_id
          ? ` (id: ${payload.email_id})`
          : "";
      setInjectEmailResult("success");
      injectSuccessTimeoutRef.current = window.setTimeout(() => {
        setInjectEmailResult(null);
        injectSuccessTimeoutRef.current = null;
      }, 1800);
      params.appendTimelineEvent({
        id: `email-inject-${new Date().toISOString()}-${sender}-${subject}`,
        timestamp: new Date().toISOString(),
        type: "attacker_action",
        granularity: "high",
        title: "Email injected to inbox",
        description: `Email ${accepted}${emailId}.`,
        details: `From: ${sender}\nSubject: ${subject}`,
      });
      setEmailFrom("");
      setEmailSubject("");
      setEmailBody("");
      setEmailMalicious(true);
      await params.refreshSessionMetadata();
    } catch (err) {
      const message = err instanceof Error ? err.message : "request failed";
      setInjectEmailError(message);
      params.appendTimelineEvent({
        id: `email-inject-error-${new Date().toISOString()}-exception`,
        timestamp: new Date().toISOString(),
        type: "system",
        granularity: "high",
        title: "Email injection failed",
        description: message,
        important: true,
      });
    } finally {
      setInjectingEmail(false);
    }
  };

  const onResetEmail = () => {
    setEmailFrom("");
    setEmailSubject("");
    setEmailBody("");
    setEmailMalicious(true);
    setInjectEmailError(null);
    if (injectSuccessTimeoutRef.current !== null) {
      window.clearTimeout(injectSuccessTimeoutRef.current);
      injectSuccessTimeoutRef.current = null;
    }
    setInjectEmailResult(null);
  };

  useEffect(() => {
    return () => {
      if (injectSuccessTimeoutRef.current !== null) {
        window.clearTimeout(injectSuccessTimeoutRef.current);
      }
    };
  }, []);

  const onToolSelect = (tool: ToolKey) => {
    setWorkspaceState((prev) => {
      if (prev.toolPaneOpen && prev.selectedTool === tool) {
        return {
          ...prev,
          toolPaneOpen: false,
        };
      }
      return {
        ...prev,
        selectedTool: tool,
        toolPaneOpen: true,
      };
    });
  };

  return {
    prompt,
    setPrompt,
    onSubmitPrompt,
    emailFrom,
    emailSubject,
    emailBody,
    emailMalicious,
    injectingEmail,
    injectEmailError,
    injectEmailResult,
    onSubmitEmail,
    onResetEmail,
    onEmailFromChange: setEmailFrom,
    onEmailSubjectChange: setEmailSubject,
    onEmailBodyChange: setEmailBody,
    onEmailMaliciousChange: setEmailMalicious,
    workspaceState,
    onToolSelect,
  };
}
