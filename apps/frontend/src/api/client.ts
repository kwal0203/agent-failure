import createClient from "openapi-fetch";
import type { components, paths } from "./generated";

type ApiErrorEnvelope = components["schemas"]["ApiErrorEnvelope"];

export function createControlPlaneClient(baseUrl: string) {
  return createClient<paths>({ baseUrl });
}

function isApiErrorEnvelope(value: unknown): value is ApiErrorEnvelope {
  if (typeof value !== "object" || value === null || !("error" in value)) {
    return false;
  }
  const error = value.error;
  return (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof error.message === "string"
  );
}

export function controlPlaneRequestError(
  error: unknown,
  response: Response,
  fallback: string,
): Error {
  if (isApiErrorEnvelope(error)) {
    return new Error(error.error.message);
  }
  if (
    typeof error === "object" &&
    error !== null &&
    "detail" in error &&
    typeof error.detail === "string"
  ) {
    return new Error(error.detail);
  }
  return new Error(`${fallback} (HTTP ${response.status})`);
}
