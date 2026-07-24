import { useQuery } from "@tanstack/react-query";
import {
  controlPlaneRequestError,
  createControlPlaneClient,
} from "../api/client";
import {
  SESSION_METADATA_POLL_BASE_MS,
  SESSION_METADATA_POLL_JITTER_RATIO,
} from "../pages/session/constants";
import { jitterDelayMs } from "../pages/session/helpers";
import type { SessionMetadata } from "../pages/session/types";
import { API_BASE, getAuthHeader } from "../pages/session/ui";

const ACTIVE_SESSION_STATES = new Set([
  "CREATED",
  "PROVISIONING",
  "ACTIVE",
  "IDLE",
]);

export const sessionMetadataQueryKey = (sessionId: string) =>
  ["sessions", sessionId] as const;

export function isActiveSession(metadata?: SessionMetadata): boolean {
  return metadata
    ? ACTIVE_SESSION_STATES.has(metadata.state.toUpperCase())
    : false;
}

export function getSessionMetadataRefetchInterval(
  metadata?: SessionMetadata,
): number | false {
  if (metadata && !isActiveSession(metadata)) {
    return false;
  }
  return jitterDelayMs(
    SESSION_METADATA_POLL_BASE_MS,
    SESSION_METADATA_POLL_JITTER_RATIO,
  );
}

export async function getSessionMetadata(
  sessionId: string,
): Promise<SessionMetadata> {
  const { data, error, response } = await createControlPlaneClient(
    API_BASE,
  ).GET("/api/v1/sessions/{session_id}", {
    params: {
      path: { session_id: sessionId },
      header: { Authorization: await getAuthHeader() },
    },
  });

  if (error || !data) {
    throw controlPlaneRequestError(error, response, "Session query failed");
  }

  return data.session;
}

export function useSessionMetadataQuery(sessionId?: string) {
  return useQuery({
    queryKey: sessionMetadataQueryKey(sessionId ?? ""),
    queryFn: () => getSessionMetadata(sessionId ?? ""),
    enabled: Boolean(sessionId),
    refetchInterval: (query) =>
      getSessionMetadataRefetchInterval(query.state.data),
  });
}
