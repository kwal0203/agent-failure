import { getCurrentAuthHeader } from "./context";

function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
}

type CreatePilotRequestPayload = {
  fullName: string;
  workEmail: string;
  university: string;
  role?: string;
  courseName?: string;
  cohortSize?: number;
  notes?: string;
};

type CreatePilotRequestResponse = {
  requestId: string;
  status: string;
  createdAt: string;
};

export async function createPilotRequest(
  payload: CreatePilotRequestPayload,
): Promise<CreatePilotRequestResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/pilot-requests`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const body = (await response.json()) as
    | CreatePilotRequestResponse
    | { detail?: string };

  if (!response.ok) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? body.detail
        : null;
    throw new Error(detail ?? "Pilot request submission failed.");
  }

  return body as CreatePilotRequestResponse;
}

export type PilotRequestItem = {
  requestId: string;
  fullName: string;
  workEmail: string;
  university: string;
  role?: string | null;
  courseName?: string | null;
  cohortSize?: number | null;
  notes?: string | null;
  sourceIp?: string | null;
  status: "new" | "contacted" | "approved" | "rejected";
  createdAt: string;
};

type ListPilotRequestsResponse = {
  items: PilotRequestItem[];
  limit: number;
  offset: number;
};

export async function listPilotRequests(params?: {
  status?: string;
  createdAfter?: string;
  limit?: number;
  offset?: number;
}): Promise<ListPilotRequestsResponse> {
  const query = new URLSearchParams();
  if (params?.status) query.set("status", params.status);
  if (params?.createdAfter) query.set("created_after", params.createdAfter);
  if (typeof params?.limit === "number")
    query.set("limit", String(params.limit));
  if (typeof params?.offset === "number")
    query.set("offset", String(params.offset));

  const suffix = query.toString() ? `?${query.toString()}` : "";
  const response = await fetch(
    `${getApiBaseUrl()}/api/v1/pilot-requests${suffix}`,
    {
      headers: {
        Authorization: getCurrentAuthHeader(),
      },
    },
  );
  const body = (await response.json()) as
    | ListPilotRequestsResponse
    | { detail?: string };
  if (!response.ok) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? body.detail
        : null;
    throw new Error(detail ?? "Failed to list pilot requests.");
  }
  return body as ListPilotRequestsResponse;
}

export async function updatePilotRequestStatus(
  requestId: string,
  status: "new" | "contacted" | "approved" | "rejected",
): Promise<PilotRequestItem> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/v1/pilot-requests/${requestId}`,
    {
      method: "PATCH",
      headers: {
        Authorization: getCurrentAuthHeader(),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status }),
    },
  );
  const body = (await response.json()) as
    | PilotRequestItem
    | { detail?: string };
  if (!response.ok) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? body.detail
        : null;
    throw new Error(detail ?? "Failed to update pilot request status.");
  }
  return body as PilotRequestItem;
}
