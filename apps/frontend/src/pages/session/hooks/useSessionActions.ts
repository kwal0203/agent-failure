import { zodResolver } from "@hookform/resolvers/zod";
import type { Dispatch, FormEvent, SetStateAction } from "react";
import { useEffect, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import type { z } from "zod";
import { useInjectSessionEmailMutation } from "../../../query/sessionMutations";
import { injectedEmailSchema } from "../../../schemas/authForms";
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
  const injectSuccessTimeoutRef = useRef<number | null>(null);
  const [prompt, setPrompt] = useState("");
  type InjectedEmailForm = z.infer<typeof injectedEmailSchema>;
  const emailForm = useForm<InjectedEmailForm>({
    resolver: zodResolver(injectedEmailSchema),
    defaultValues: { emailFrom: "", emailSubject: "", emailBody: "" },
    mode: "onChange",
  });
  const emailFrom = useWatch({ control: emailForm.control, name: "emailFrom" });
  const emailSubject = useWatch({
    control: emailForm.control,
    name: "emailSubject",
  });
  const emailBody = useWatch({ control: emailForm.control, name: "emailBody" });
  const injectEmailMutation = useInjectSessionEmailMutation(params.sessionId);
  const [workspaceState, setWorkspaceState] = useState<SessionWorkspaceState>({
    selectedTool: null,
    toolPaneOpen: false,
  });
  const fromValidationError =
    emailForm.formState.errors.emailFrom?.message ?? null;

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

  const submitEmail = async (values: InjectedEmailForm) => {
    if (!params.sessionId || params.interactionLocked) return;

    injectEmailMutation.reset();
    if (injectSuccessTimeoutRef.current !== null) {
      window.clearTimeout(injectSuccessTimeoutRef.current);
      injectSuccessTimeoutRef.current = null;
    }

    try {
      await injectEmailMutation.mutateAsync({
        emailFrom: values.emailFrom,
        emailSubject: values.emailSubject,
        emailBody: values.emailBody,
      });
      injectSuccessTimeoutRef.current = window.setTimeout(() => {
        injectEmailMutation.reset();
        injectSuccessTimeoutRef.current = null;
      }, 1800);
      emailForm.reset();
    } catch {
      return;
    }
  };
  const onSubmitEmail = (event: FormEvent<HTMLFormElement>) => {
    void emailForm.handleSubmit(submitEmail)(event);
  };

  const onResetEmail = () => {
    emailForm.reset();
    if (injectSuccessTimeoutRef.current !== null) {
      window.clearTimeout(injectSuccessTimeoutRef.current);
      injectSuccessTimeoutRef.current = null;
    }
    injectEmailMutation.reset();
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
    emailForm.formState.errors.emailSubject?.message ??
    emailForm.formState.errors.emailBody?.message ??
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
    onEmailFromChange: (value: string) =>
      emailForm.setValue("emailFrom", value, {
        shouldDirty: true,
        shouldValidate: true,
      }),
    onEmailSubjectChange: (value: string) =>
      emailForm.setValue("emailSubject", value, {
        shouldDirty: true,
        shouldValidate: true,
      }),
    onEmailBodyChange: (value: string) =>
      emailForm.setValue("emailBody", value, {
        shouldDirty: true,
        shouldValidate: true,
      }),
    workspaceState,
    onToolSelect,
  };
}
