import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithQueryClient } from "../../test/renderWithQueryClient";
import PilotRequestsAdminPage from "./PilotRequestsAdminPage";

const pilotRequestApiMocks = vi.hoisted(() => ({
  approveAndProvisionPilotRequest: vi.fn(),
  listPilotRequests: vi.fn(),
  provisionPilotRequest: vi.fn(),
  updatePilotRequestStatus: vi.fn(),
}));

vi.mock("../../auth/pilotRequests", () => pilotRequestApiMocks);

type PilotRequestStatus =
  | "new"
  | "contacted"
  | "approved"
  | "approved_provisioning_failed"
  | "rejected";

function pilotRequest(status: PilotRequestStatus = "new") {
  return {
    requestId: "request-12345678",
    fullName: "Kane Wilson",
    workEmail: "kane@example.edu",
    university: "Example University",
    courseName: "Security 101",
    cohortSize: 30,
    status,
    createdAt: "2026-07-23T12:00:00Z",
  };
}

function listResponse(status: PilotRequestStatus = "new") {
  return {
    items: [pilotRequest(status)],
    limit: 100,
    offset: 0,
  };
}

describe("PilotRequestsAdminPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pilotRequestApiMocks.listPilotRequests.mockResolvedValue(listResponse());
  });

  it("keys the request list by the selected status filter", async () => {
    renderWithQueryClient(<PilotRequestsAdminPage />);

    expect(await screen.findByText("Kane Wilson")).toBeVisible();
    expect(pilotRequestApiMocks.listPilotRequests).toHaveBeenCalledWith({
      status: undefined,
      limit: 100,
      offset: 0,
    });

    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "contacted" },
    });

    await waitFor(() => {
      expect(pilotRequestApiMocks.listPilotRequests).toHaveBeenCalledWith({
        status: "contacted",
        limit: 100,
        offset: 0,
      });
    });
  });

  it("updates status and refreshes the cached request list", async () => {
    let resolveUpdate: (value: ReturnType<typeof pilotRequest>) => void = () =>
      undefined;
    pilotRequestApiMocks.updatePilotRequestStatus.mockReturnValue(
      new Promise((resolve) => {
        resolveUpdate = resolve;
      }),
    );

    renderWithQueryClient(<PilotRequestsAdminPage />);

    const updateButton = await screen.findByRole("button", {
      name: "Mark contacted",
    });
    fireEvent.click(updateButton);

    await waitFor(() => {
      expect(
        pilotRequestApiMocks.updatePilotRequestStatus,
      ).toHaveBeenCalledWith("request-12345678", "contacted");
    });
    expect(updateButton).toBeDisabled();

    resolveUpdate(pilotRequest("contacted"));
    await waitFor(() => {
      expect(pilotRequestApiMocks.listPilotRequests).toHaveBeenCalledTimes(2);
    });
  });

  it("approves and provisions a contacted request, then refreshes the list", async () => {
    pilotRequestApiMocks.listPilotRequests.mockResolvedValue(
      listResponse("contacted"),
    );
    pilotRequestApiMocks.approveAndProvisionPilotRequest.mockResolvedValue({
      pilotRequest: pilotRequest("approved"),
      isRetry: false,
      runCorrelationId: "run-123",
      approvedStep: true,
    });

    renderWithQueryClient(<PilotRequestsAdminPage />);

    fireEvent.click(
      await screen.findByRole("button", { name: "Approve + Provision" }),
    );

    await waitFor(() => {
      expect(
        pilotRequestApiMocks.approveAndProvisionPilotRequest,
      ).toHaveBeenCalledWith(
        "request-12345678",
        expect.objectContaining({
          courseId: "security-101-request-",
          courseName: "Security 101",
          instructorEmail: "kane@example.edu",
          classCodeMaxUses: 60,
          createInstructorIfMissing: true,
        }),
      );
    });
    expect(
      await screen.findByRole("heading", {
        name: "Approve + Provision Result",
      }),
    ).toBeVisible();
    expect(pilotRequestApiMocks.listPilotRequests).toHaveBeenCalledTimes(2);
  });

  it("uses the approve-and-provision mutation to retry failed provisioning", async () => {
    pilotRequestApiMocks.listPilotRequests.mockResolvedValue(
      listResponse("approved_provisioning_failed"),
    );
    pilotRequestApiMocks.approveAndProvisionPilotRequest.mockResolvedValue({
      pilotRequest: pilotRequest("approved"),
      isRetry: true,
      runCorrelationId: "run-retry",
      approvedStep: true,
    });

    renderWithQueryClient(<PilotRequestsAdminPage />);

    fireEvent.click(
      await screen.findByRole("button", { name: "Retry Provisioning" }),
    );

    await waitFor(() => {
      expect(
        pilotRequestApiMocks.approveAndProvisionPilotRequest,
      ).toHaveBeenCalledOnce();
    });
    expect(await screen.findByText(/Retry: yes/)).toBeVisible();
    expect(pilotRequestApiMocks.listPilotRequests).toHaveBeenCalledTimes(2);
  });

  it("manually provisions a pilot and refreshes the list", async () => {
    pilotRequestApiMocks.listPilotRequests.mockResolvedValue(
      listResponse("contacted"),
    );
    pilotRequestApiMocks.provisionPilotRequest.mockResolvedValue({
      created: true,
      provisioningSummary: {
        pilotRequestId: "request-12345678",
        courseId: "security-101-request-",
        courseName: "Security 101",
        classCode: "SECURITY-REQU",
        classCodeStatus: "active",
        instructorEmail: "kane@example.edu",
        provisionedAt: "2026-07-23T12:00:00Z",
      },
    });

    renderWithQueryClient(<PilotRequestsAdminPage />);

    fireEvent.click(
      await screen.findByRole("button", { name: "Provision Pilot" }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Provision Pilot" }));

    await waitFor(() => {
      expect(pilotRequestApiMocks.provisionPilotRequest).toHaveBeenCalledWith(
        "request-12345678",
        {
          courseId: "security-101-request-",
          courseName: "Security 101",
          classCode: "SECURITY-REQU",
          instructorEmail: "kane@example.edu",
          maxUses: 60,
        },
      );
    });
    expect(
      await screen.findByRole("heading", { name: "Provisioning Summary" }),
    ).toBeVisible();
    expect(pilotRequestApiMocks.listPilotRequests).toHaveBeenCalledTimes(2);
  });
});
