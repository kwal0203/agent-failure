import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useEffect, useRef, useState } from "react";
import { useInjectSessionEmailMutation } from "../../../query/sessionMutations";
import type {
  AgentStatus,
  SessionWorkspaceState,
  ToolKey,
  TranscriptEntry,
} from "../types";

type UseSessionActionsParams = {
  sessionId?: string;
  canSend: boolean;
  interactionLocked: boolean;
  sendPrompt: (text: string) => void;
  setTranscriptEntries: Dispatch<SetStateAction<TranscriptEntry[]>>;
  setIsAwaitingResponse: Dispatch<SetStateAction<boolean>>;
  resetActiveStream: () => void;
  setAgentStatus: (status: AgentStatus) => void;
};

export function useSessionActions(params: UseSessionActionsParams) {
  const isValidEmail = (value: string): boolean => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  };

  const injectSuccessTimeoutRef = useRef<number | null>(null);
  const [prompt, setPrompt] = useState("");
  const [emailFrom, setEmailFrom] = useState("");
  const [emailSubject, setEmailSubject] = useState("");
  const [emailBody, setEmailBody] = useState("");
  const [injectEmailValidationError, setInjectEmailValidationError] = useState<
    string | null
  >(null);
  const [emailFromTouched, setEmailFromTouched] = useState(false);
  const injectEmailMutation = useInjectSessionEmailMutation(params.sessionId);
  const [workspaceState, setWorkspaceState] = useState<SessionWorkspaceState>({
    selectedTool: null,
    toolPaneOpen: false,
  });
  const fromValidationError =
    emailFromTouched && !emailFrom.trim()
      ? "From is required."
      : emailFrom.trim() && !isValidEmail(emailFrom.trim())
        ? "From must be a valid email address."
        : null;

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
    if (!params.sessionId || params.interactionLocked) return;

    const sender = emailFrom.trim();
    const subject = emailSubject.trim();
    const body = emailBody.trim();
    if (!sender || !subject || !body) {
      setInjectEmailValidationError("From, subject, and body are required.");
      return;
    }
    if (!isValidEmail(sender)) {
      setInjectEmailValidationError("From must be a valid email address.");
      return;
    }

    setInjectEmailValidationError(null);
    injectEmailMutation.reset();
    if (injectSuccessTimeoutRef.current !== null) {
      window.clearTimeout(injectSuccessTimeoutRef.current);
      injectSuccessTimeoutRef.current = null;
    }

    try {
      await injectEmailMutation.mutateAsync({
        emailFrom: sender,
        emailSubject: subject,
        emailBody: body,
      });
      injectSuccessTimeoutRef.current = window.setTimeout(() => {
        injectEmailMutation.reset();
        injectSuccessTimeoutRef.current = null;
      }, 1800);
      setEmailFromTouched(false);
      setEmailFrom("");
      setEmailSubject("");
      setEmailBody("");
    } catch {
      return;
    }
  };

  const onResetEmail = () => {
    setEmailFrom("");
    setEmailSubject("");
    setEmailBody("");
    setEmailFromTouched(false);
    setInjectEmailValidationError(null);
    if (injectSuccessTimeoutRef.current !== null) {
      window.clearTimeout(injectSuccessTimeoutRef.current);
      injectSuccessTimeoutRef.current = null;
    }
    injectEmailMutation.reset();
  };

  const onEmailFromChange = (value: string) => {
    setEmailFromTouched(true);
    setEmailFrom(value);
  };

  useEffect(() => {
    return () => {
      if (injectSuccessTimeoutRef.current !== null) {
        window.clearTimeout(injectSuccessTimeoutRef.current);
      }
    };
  }, []);

  const onToolSelect = (tool: ToolKey) => {
    if (params.interactionLocked) {
      return;
    }
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

  const injectEmailError =
    injectEmailValidationError ??
    (injectEmailMutation.error instanceof Error
      ? injectEmailMutation.error.message
      : null);

  return {
    prompt,
    setPrompt,
    onSubmitPrompt,
    emailFrom,
    emailSubject,
    emailBody,
    injectingEmail: injectEmailMutation.isPending,
    fromValidationError,
    injectEmailError,
    injectEmailResult: injectEmailMutation.isSuccess ? "success" : null,
    onSubmitEmail,
    onResetEmail,
    onEmailFromChange,
    onEmailSubjectChange: setEmailSubject,
    onEmailBodyChange: setEmailBody,
    workspaceState,
    onToolSelect,
  };
}
