import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  controlPlaneRequestError,
  createControlPlaneClient,
} from "../api/client";
import {
  createSessionForLab,
  type LabDifficulty,
} from "../pages/labCatalogApi";
import type {
  InjectSessionEmailResponse,
  MarkSessionHintsSeenResponse,
} from "../pages/session/types";
import { API_BASE, getAuthHeader } from "../pages/session/ui";
import { sessionMetadataQueryKey } from "./sessionMetadata";
import { sessionTraceQueryKey } from "./sessionTrace";

type CreateSessionVariables = {
  labId: string;
  labDifficulty: LabDifficulty;
};

export type InjectSessionEmailVariables = {
  emailFrom: string;
  emailSubject: string;
  emailBody: string;
};

export const sessionMutationKeys = {
  create: (apiBaseUrl: string) => ["sessions", "create", apiBaseUrl] as const,
  stop: (sessionId: string) =>
    ["sessions", sessionId, "mutation", "stop"] as const,
  injectEmail: (sessionId: string) =>
    ["sessions", sessionId, "mutation", "inject-email"] as const,
  markHintsSeen: (sessionId: string) =>
    ["sessions", sessionId, "mutation", "mark-hints-seen"] as const,
  markFeedbackSeen: (sessionId: string) =>
    ["sessions", sessionId, "mutation", "mark-feedback-seen"] as const,
};

function useInvalidateSessionData(sessionId?: string) {
  const queryClient = useQueryClient();
  return async (includeTrace: boolean) => {
    if (!sessionId) return;
    const invalidations: Promise<void>[] = [
      queryClient.invalidateQueries({
        queryKey: sessionMetadataQueryKey(sessionId),
        exact: true,
      }),
    ];
    if (includeTrace) {
      invalidations.push(
        queryClient.invalidateQueries({
          queryKey: sessionTraceQueryKey(sessionId),
          exact: true,
        }),
      );
    }
    await Promise.all(invalidations);
  };
}

export function useCreateSessionMutation(apiBaseUrl: string) {
  return useMutation({
    mutationKey: sessionMutationKeys.create(apiBaseUrl),
    mutationFn: ({
      labId,
      labDifficulty,
    }: CreateSessionVariables): Promise<string> =>
      createSessionForLab(apiBaseUrl, labId, labDifficulty),
  });
}

export function useStopSessionMutation(sessionId?: string) {
  const invalidateSessionData = useInvalidateSessionData(sessionId);
  return useMutation({
    mutationKey: sessionMutationKeys.stop(sessionId ?? ""),
    mutationFn: async () => {
      if (!sessionId) throw new Error("Session ID is required");
      const { error, response } = await createControlPlaneClient(API_BASE).POST(
        "/api/v1/sessions/{session_id}/stop",
        {
          params: {
            path: { session_id: sessionId },
            header: {
              Authorization: await getAuthHeader(),
              "Idempotency-Key": `stop-session:${sessionId}`,
            },
          },
        },
      );
      if (error) {
        throw controlPlaneRequestError(
          error,
          response,
          "Failed to stop session",
        );
      }
    },
    onSuccess: () => invalidateSessionData(true),
  });
}

export function useInjectSessionEmailMutation(sessionId?: string) {
  const invalidateSessionData = useInvalidateSessionData(sessionId);
  return useMutation({
    mutationKey: sessionMutationKeys.injectEmail(sessionId ?? ""),
    mutationFn: async ({
      emailFrom,
      emailSubject,
      emailBody,
    }: InjectSessionEmailVariables): Promise<InjectSessionEmailResponse> => {
      if (!sessionId) throw new Error("Session ID is required");
      const { data, error, response } = await createControlPlaneClient(
        API_BASE,
      ).POST("/api/v1/sessions/{session_id}/inbox/email", {
        params: {
          path: { session_id: sessionId },
          header: { Authorization: await getAuthHeader() },
        },
        body: {
          email_from: emailFrom,
          email_subject: emailSubject,
          email_body: emailBody,
          source: "learner",
        },
      });
      if (error || !data) {
        throw controlPlaneRequestError(
          error,
          response,
          "Failed to inject email",
        );
      }
      return data;
    },
    onSuccess: () => invalidateSessionData(true),
  });
}

export function useMarkSessionHintsSeenMutation(sessionId?: string) {
  const invalidateSessionData = useInvalidateSessionData(sessionId);
  return useMutation({
    mutationKey: sessionMutationKeys.markHintsSeen(sessionId ?? ""),
    mutationFn: async (): Promise<MarkSessionHintsSeenResponse> => {
      if (!sessionId) throw new Error("Session ID is required");
      const { data, error, response } = await createControlPlaneClient(
        API_BASE,
      ).POST("/api/v1/sessions/{session_id}/hints/mark-seen", {
        params: {
          path: { session_id: sessionId },
          header: { Authorization: await getAuthHeader() },
        },
      });
      if (error || !data) {
        throw controlPlaneRequestError(
          error,
          response,
          "Failed to mark hints as seen",
        );
      }
      return data;
    },
    onSuccess: () => invalidateSessionData(false),
  });
}

export function useMarkSessionFeedbackSeenMutation(sessionId?: string) {
  const invalidateSessionData = useInvalidateSessionData(sessionId);
  return useMutation({
    mutationKey: sessionMutationKeys.markFeedbackSeen(sessionId ?? ""),
    mutationFn: async (): Promise<MarkSessionHintsSeenResponse> => {
      if (!sessionId) throw new Error("Session ID is required");
      const { data, error, response } = await createControlPlaneClient(
        API_BASE,
      ).POST("/api/v1/sessions/{session_id}/feedback/mark-seen", {
        params: {
          path: { session_id: sessionId },
          header: { Authorization: await getAuthHeader() },
        },
      });
      if (error || !data) {
        throw controlPlaneRequestError(
          error,
          response,
          "Failed to mark feedback as seen",
        );
      }
      return data;
    },
    onSuccess: () => invalidateSessionData(false),
  });
}
