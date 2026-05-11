import { getCurrentAuthHeader } from "./context";

function getApiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
}

export const PENDING_ENROLLMENT_TOKEN_KEY =
  "agentfailure.auth.pendingEnrollmentToken";
export const ENROLLMENT_REDEEM_ERROR_KEY =
  "agentfailure.auth.enrollmentRedeemError";

type ValidateClassCodeResponse = {
  valid: boolean;
  enrollmentToken?: string;
  error?: string;
};

type RedeemEnrollmentResponse = {
  enrolled: boolean;
  error?: string;
};

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
  const response = await fetch(
    `${getApiBaseUrl()}/api/v1/enrollment/validate-class-code`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        classCode: classCode.trim(),
        email: email.trim().toLowerCase(),
      }),
    },
  );

  const payload = (await response.json()) as ValidateClassCodeResponse;

  if (!response.ok || payload.valid !== true || !payload.enrollmentToken) {
    throw new Error(payload.error ?? "Class code validation failed.");
  }

  return payload.enrollmentToken;
}

export async function redeemEnrollmentToken(
  enrollmentToken: string,
): Promise<void> {
  const response = await fetch(`${getApiBaseUrl()}/api/v1/enrollment/redeem`, {
    method: "POST",
    headers: {
      Authorization: getCurrentAuthHeader(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      enrollmentToken,
    }),
  });

  const payload = (await response.json()) as RedeemEnrollmentResponse;

  if (!response.ok || payload.enrolled !== true) {
    throw new Error(payload.error ?? "Enrollment token redemption failed.");
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
