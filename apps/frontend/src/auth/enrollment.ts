import { getCurrentAuthHeader } from "./context";

const ENROLLMENT_API_ENABLED =
  (import.meta.env.VITE_ENROLLMENT_API_ENABLED ?? "false").toLowerCase() ===
  "true";
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const PENDING_ENROLLMENT_TOKEN_KEY =
  "agentfailure.auth.pendingEnrollmentToken";

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
  return ENROLLMENT_API_ENABLED;
}

export async function validateClassCode(
  classCode: string,
  email: string,
): Promise<string> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/enrollment/validate-class-code`,
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
  const response = await fetch(`${API_BASE_URL}/api/v1/enrollment/redeem`, {
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
  if (!ENROLLMENT_API_ENABLED) {
    return;
  }

  const token = window.sessionStorage.getItem(PENDING_ENROLLMENT_TOKEN_KEY);
  if (!token) {
    return;
  }

  await redeemEnrollmentToken(token);
  window.sessionStorage.removeItem(PENDING_ENROLLMENT_TOKEN_KEY);
}
