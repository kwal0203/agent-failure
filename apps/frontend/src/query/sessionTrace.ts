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
import { mapPersistedTraceToTimelineEvent } from "../pages/session/timelineEventMapper";
import type { SessionTraceEvent, TimelineEvent } from "../pages/session/types";
import { API_BASE, getAuthHeader } from "../pages/session/ui";
import { isActiveSession, useSessionMetadataQuery } from "./sessionMetadata";

export type SessionTraceData = {
  events: SessionTraceEvent[];
  timelineEvents: TimelineEvent[];
};

export const sessionTraceQueryKey = (sessionId: string) =>
  ["sessions", sessionId, "trace"] as const;

export function getSessionTraceRefetchInterval(
  sessionIsActive?: boolean,
): number | false {
  if (sessionIsActive === false) {
    return false;
  }
  return jitterDelayMs(
    SESSION_METADATA_POLL_BASE_MS,
    SESSION_METADATA_POLL_JITTER_RATIO,
  );
}

export async function getSessionTrace(
  sessionId: string,
): Promise<SessionTraceData> {
  const { data, error, response } = await createControlPlaneClient(
    API_BASE,
  ).GET("/api/v1/sessions/{session_id}/trace", {
    params: {
      path: { session_id: sessionId },
      header: { Authorization: await getAuthHeader() },
    },
  });

  if (error || !data) {
    throw controlPlaneRequestError(
      error,
      response,
      "Session trace query failed",
    );
  }

  const events = data.events;
  const timelineEvents = events
    .map((event) => mapPersistedTraceToTimelineEvent(event))
    .filter((event): event is TimelineEvent => event !== null);

  return { events, timelineEvents };
}

export function useSessionTraceQuery(sessionId?: string) {
  const metadataQuery = useSessionMetadataQuery(sessionId);
  const sessionIsActive = metadataQuery.data
    ? isActiveSession(metadataQuery.data)
    : undefined;

  return useQuery({
    queryKey: sessionTraceQueryKey(sessionId ?? ""),
    queryFn: () => getSessionTrace(sessionId ?? ""),
    enabled: Boolean(sessionId),
    refetchInterval: () => getSessionTraceRefetchInterval(sessionIsActive),
  });
}
