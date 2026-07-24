import {
  controlPlaneRequestError,
  createControlPlaneClient,
} from "../api/client";
import { getCurrentAuthHeader } from "./session";

function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
}

export const PENDING_ENROLLMENT_TOKEN_KEY =
  "agentfailure.auth.pendingEnrollmentToken";
export const ENROLLMENT_REDEEM_ERROR_KEY =
  "agentfailure.auth.enrollmentRedeemError";

export function isEnrollmentApiEnabled(): boolean {
  return (
    (import.meta.env.VITE_ENROLLMENT_API_ENABLED ?? "false").toLowerCase() ===
    "true"
  );
}

export async function validateClassCode(
  classCode: string,
  email: string,
): Promise<string> {
  const { data, error, response } = await createControlPlaneClient(
    getApiBaseUrl(),
  ).POST("/api/v1/enrollment/validate-class-code", {
    body: {
      classCode: classCode.trim(),
      email: email.trim().toLowerCase(),
    },
  });

  if (error || !data) {
    throw controlPlaneRequestError(
      error,
      response,
      "Class code validation failed",
    );
  }
  if (!data.valid || !data.enrollmentToken) {
    throw new Error(data.error ?? "Class code validation failed.");
  }

  return data.enrollmentToken;
}

export async function redeemEnrollmentToken(
  enrollmentToken: string,
): Promise<void> {
  const { data, error, response } = await createControlPlaneClient(
    getApiBaseUrl(),
  ).POST("/api/v1/enrollment/redeem", {
    params: {
      header: {
        Authorization: await getCurrentAuthHeader(),
      },
    },
    body: {
      enrollmentToken,
    },
  });

  if (error || !data) {
    throw controlPlaneRequestError(
      error,
      response,
      "Enrollment token redemption failed",
    );
  }
  if (!data.enrolled) {
    throw new Error(data.error ?? "Enrollment token redemption failed.");
  }
}

export async function tryRedeemPendingEnrollmentToken(): Promise<void> {
  if (!isEnrollmentApiEnabled()) {
    return;
  }

  const token = window.sessionStorage.getItem(PENDING_ENROLLMENT_TOKEN_KEY);
  if (!token) {
    return;
  }

  try {
    await redeemEnrollmentToken(token);
    window.sessionStorage.removeItem(PENDING_ENROLLMENT_TOKEN_KEY);
    window.sessionStorage.removeItem(ENROLLMENT_REDEEM_ERROR_KEY);
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Enrollment token redemption failed.";
    window.sessionStorage.setItem(ENROLLMENT_REDEEM_ERROR_KEY, message);
  }
}

export function getEnrollmentRedeemError(): string | null {
  return window.sessionStorage.getItem(ENROLLMENT_REDEEM_ERROR_KEY);
}

export function clearEnrollmentRedeemError(): void {
  window.sessionStorage.removeItem(ENROLLMENT_REDEEM_ERROR_KEY);
}

export function clearPendingEnrollmentToken(): void {
  window.sessionStorage.removeItem(PENDING_ENROLLMENT_TOKEN_KEY);
}
