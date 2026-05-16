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
