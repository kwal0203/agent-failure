import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useEffect, useRef, useState } from "react";
import type {
  AgentStatus,
  InjectSessionEmailResponse,
  SessionWorkspaceState,
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
  refreshSessionMetadata: () => Promise<void>;
};

export function useSessionActions(params: UseSessionActionsParams) {
  const injectSuccessTimeoutRef = useRef<number | null>(null);
  const [prompt, setPrompt] = useState("");
  const [emailFrom, setEmailFrom] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");
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
        return;
      }

      setInjectEmailResult("success");
      injectSuccessTimeoutRef.current = window.setTimeout(() => {
        setInjectEmailResult(null);
        injectSuccessTimeoutRef.current = null;
      }, 1800);
      setEmailFrom("");
      setEmailSubject("");
      setEmailBody("");
      await params.refreshSessionMetadata();
    } catch (err) {
      const message = err instanceof Error ? err.message : "request failed";
      setInjectEmailError(message);
    } finally {
      setInjectingEmail(false);
    }
  };

  const onResetEmail = () => {
    setEmailFrom("");
    setEmailSubject("");
    setEmailBody("");
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
    injectingEmail,
    injectEmailError,
    injectEmailResult,
    onSubmitEmail,
    onResetEmail,
    onEmailFromChange: setEmailFrom,
    onEmailSubjectChange: setEmailSubject,
    onEmailBodyChange: setEmailBody,
    workspaceState,
    onToolSelect,
  };
}
