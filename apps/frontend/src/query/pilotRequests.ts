import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type ApproveAndProvisionPayload,
  approveAndProvisionPilotRequest,
  listPilotRequests,
  type PilotRequestItem,
  type ProvisionPilotPayload,
  provisionPilotRequest,
  updatePilotRequestStatus,
} from "../auth/pilotRequests";

type PilotRequestStatus = PilotRequestItem["status"];

type UpdatePilotRequestStatusVariables = {
  requestId: string;
  status: PilotRequestStatus;
};

type ApproveAndProvisionVariables = {
  requestId: string;
  payload: ApproveAndProvisionPayload;
};

type ProvisionPilotVariables = {
  requestId: string;
  payload: ProvisionPilotPayload;
};

export const pilotRequestQueryKeys = {
  all: ["pilot-requests"] as const,
  lists: () => [...pilotRequestQueryKeys.all, "list"] as const,
  list: (status?: PilotRequestStatus) =>
    [...pilotRequestQueryKeys.lists(), { status: status ?? "all" }] as const,
};

export const pilotRequestMutationKeys = {
  updateStatus: ["pilot-requests", "update-status"] as const,
  approveAndProvision: ["pilot-requests", "approve-and-provision"] as const,
  provision: ["pilot-requests", "provision"] as const,
};

export function usePilotRequestsQuery(status?: PilotRequestStatus) {
  return useQuery({
    queryKey: pilotRequestQueryKeys.list(status),
    queryFn: () =>
      listPilotRequests({
        status,
        limit: 100,
        offset: 0,
      }),
  });
}

function useRefreshPilotRequestLists() {
  const queryClient = useQueryClient();
  return () =>
    queryClient.invalidateQueries({
      queryKey: pilotRequestQueryKeys.lists(),
    });
}

export function useUpdatePilotRequestStatusMutation() {
  const refreshLists = useRefreshPilotRequestLists();
  return useMutation({
    mutationKey: pilotRequestMutationKeys.updateStatus,
    mutationFn: ({ requestId, status }: UpdatePilotRequestStatusVariables) =>
      updatePilotRequestStatus(requestId, status),
    onSuccess: refreshLists,
  });
}

export function useApproveAndProvisionPilotRequestMutation() {
  const refreshLists = useRefreshPilotRequestLists();
  return useMutation({
    mutationKey: pilotRequestMutationKeys.approveAndProvision,
    mutationFn: ({ requestId, payload }: ApproveAndProvisionVariables) =>
      approveAndProvisionPilotRequest(requestId, payload),
    onSuccess: refreshLists,
  });
}

export function useProvisionPilotRequestMutation() {
  const refreshLists = useRefreshPilotRequestLists();
  return useMutation({
    mutationKey: pilotRequestMutationKeys.provision,
    mutationFn: ({ requestId, payload }: ProvisionPilotVariables) =>
      provisionPilotRequest(requestId, payload),
    onSuccess: refreshLists,
  });
}
