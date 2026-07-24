import {
  controlPlaneRequestError,
  createControlPlaneClient,
} from "../api/client";
import type { components } from "../api/generated";
import { getApiBaseUrl } from "../config";
import type { PilotLead } from "../schemas/pilotRequest";
import { getCurrentAuthHeader } from "./session";

export async function createPilotRequest(payload: PilotLead): Promise<void> {
  const response = await fetch("/api/pilot-request", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  });

  const body = (await response.json().catch(() => null)) as {
    detail?: string;
  } | null;

  if (!response.ok) {
    throw new Error(body?.detail ?? "Pilot request submission failed.");
  }
}

export type PilotRequestStatus =
  | "new"
  | "contacted"
  | "approved"
  | "approved_provisioning_failed"
  | "rejected";
export type PilotRequestItem = Omit<
  components["schemas"]["PilotRequestItemResponse"],
  "status"
> & {
  status: PilotRequestStatus;
};
type ListPilotRequestsResponse = Omit<
  components["schemas"]["ListPilotRequestsResponse"],
  "items"
> & {
  items: PilotRequestItem[];
};

function normalizePilotRequestItem(
  item: components["schemas"]["PilotRequestItemResponse"],
): PilotRequestItem {
  switch (item.status) {
    case "new":
    case "contacted":
    case "approved":
    case "approved_provisioning_failed":
    case "rejected":
      return { ...item, status: item.status };
    default:
      throw new Error(`Unsupported pilot request status: ${item.status}`);
  }
}

export async function listPilotRequests(params?: {
  status?: string;
  createdAfter?: string;
  limit?: number;
  offset?: number;
}): Promise<ListPilotRequestsResponse> {
  const { data, error, response } = await createControlPlaneClient(
    getApiBaseUrl(),
  ).GET("/api/v1/pilot-requests", {
    params: {
      query: {
        status: params?.status,
        created_after: params?.createdAfter,
        limit: params?.limit,
        offset: params?.offset,
      },
      header: {
        Authorization: await getCurrentAuthHeader(),
      },
    },
  });
  if (error || !data) {
    throw controlPlaneRequestError(
      error,
      response,
      "Failed to list pilot requests",
    );
  }
  return {
    ...data,
    items: data.items.map(normalizePilotRequestItem),
  };
}

export async function updatePilotRequestStatus(
  requestId: string,
  status:
    | "new"
    | "contacted"
    | "approved"
    | "approved_provisioning_failed"
    | "rejected",
): Promise<PilotRequestItem> {
  const { data, error, response } = await createControlPlaneClient(
    getApiBaseUrl(),
  ).PATCH("/api/v1/pilot-requests/{request_id}", {
    params: {
      path: { request_id: requestId },
      header: {
        Authorization: await getCurrentAuthHeader(),
      },
    },
    body: { status },
  });
  if (error || !data) {
    throw controlPlaneRequestError(
      error,
      response,
      "Failed to update pilot request status",
    );
  }
  return normalizePilotRequestItem(data);
}

export type ApproveAndProvisionPayload =
  components["schemas"]["ApproveAndProvisionRequest"];
export type ProvisionPilotPayload =
  components["schemas"]["ProvisionPilotRequestPayload"];
export type ProvisionPilotResponse =
  components["schemas"]["ProvisionPilotRequestResponse"];
export type ApproveAndProvisionResponse = Omit<
  components["schemas"]["ApproveAndProvisionResponse"],
  "pilotRequest"
> & {
  pilotRequest: PilotRequestItem;
};

export async function approveAndProvisionPilotRequest(
  requestId: string,
  payload: ApproveAndProvisionPayload,
): Promise<ApproveAndProvisionResponse> {
  const { data, error, response } = await createControlPlaneClient(
    getApiBaseUrl(),
  ).POST("/api/v1/pilot-requests/{request_id}/approve-and-provision", {
    params: {
      path: { request_id: requestId },
      header: {
        Authorization: await getCurrentAuthHeader(),
      },
    },
    body: payload,
  });
  if (error || !data) {
    throw controlPlaneRequestError(
      error,
      response,
      "Failed to approve and provision pilot request",
    );
  }
  return {
    ...data,
    pilotRequest: normalizePilotRequestItem(data.pilotRequest),
  };
}

export async function provisionPilotRequest(
  requestId: string,
  payload: ProvisionPilotPayload,
): Promise<ProvisionPilotResponse> {
  const { data, error, response } = await createControlPlaneClient(
    getApiBaseUrl(),
  ).POST("/api/v1/pilot-requests/{request_id}/provision", {
    params: {
      path: { request_id: requestId },
      header: {
        Authorization: await getCurrentAuthHeader(),
      },
    },
    body: payload,
  });
  if (error || !data) {
    throw controlPlaneRequestError(
      error,
      response,
      "Failed to provision pilot request",
    );
  }
  return data;
}
