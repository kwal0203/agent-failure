import { useMutation } from "@tanstack/react-query";
import { redeemEnrollmentToken, validateClassCode } from "../auth/enrollment";
import { createPilotRequest } from "../auth/pilotRequests";
import type { PilotLead } from "../schemas/pilotRequest";

export type ValidateClassCodeVariables = {
  classCode: string;
  email: string;
};

export const publicMutationKeys = {
  validateClassCode: ["enrollment", "validate-class-code"] as const,
  redeemEnrollment: ["enrollment", "redeem"] as const,
  submitPilotRequest: ["pilot-requests", "submit"] as const,
};

export function useValidateClassCodeMutation() {
  return useMutation({
    mutationKey: publicMutationKeys.validateClassCode,
    mutationFn: ({ classCode, email }: ValidateClassCodeVariables) =>
      validateClassCode(classCode, email),
  });
}

export function useRedeemEnrollmentMutation() {
  return useMutation({
    mutationKey: publicMutationKeys.redeemEnrollment,
    mutationFn: (enrollmentToken: string) =>
      redeemEnrollmentToken(enrollmentToken),
  });
}

export function useSubmitPilotRequestMutation() {
  return useMutation({
    mutationKey: publicMutationKeys.submitPilotRequest,
    mutationFn: (lead: PilotLead) => createPilotRequest(lead),
  });
}
