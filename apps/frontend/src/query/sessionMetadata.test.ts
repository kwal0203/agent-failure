import { afterEach, describe, expect, it, vi } from "vitest";
import type { SessionMetadata } from "../pages/session/types";
import {
  getSessionMetadataRefetchInterval,
  isActiveSession,
  sessionMetadataQueryKey,
} from "./sessionMetadata";

function metadataWithState(state: string): SessionMetadata {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    lab_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    lab_version_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    state,
    runtime_substate: null,
    resume_mode: "fresh",
    last_transition_reason: null,
    interactive: true,
    created_at: "2026-07-23T12:00:00Z",
    started_at: null,
    ended_at: null,
    completion_status: "in_progress",
    completed_at: null,
    completion_reason_code: null,
    provisioning_stalled: false,
    provisioning_stall_reason_code: null,
    progress_chips: [],
    hints: [],
    unread_hint_count: 0,
    feedback_items: [],
    feedback: [],
    unread_feedback_count: 0,
    runtime_files: [],
  };
}

describe("session metadata query", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses a cache key scoped to the session", () => {
    expect(
      sessionMetadataQueryKey("11111111-1111-1111-1111-111111111111"),
    ).toEqual(["sessions", "11111111-1111-1111-1111-111111111111"]);
  });

  it.each(["CREATED", "PROVISIONING", "ACTIVE", "IDLE"])(
    "continues polling while the session is %s",
    (state) => {
      vi.spyOn(Math, "random").mockReturnValue(0.5);

      const metadata = metadataWithState(state);

      expect(isActiveSession(metadata)).toBe(true);
      expect(getSessionMetadataRefetchInterval(metadata)).toBe(1000);
    },
  );

  it.each(["COMPLETED", "FAILED", "STOPPED"])(
    "stops polling while the session is %s",
    (state) => {
      const metadata = metadataWithState(state);

      expect(isActiveSession(metadata)).toBe(false);
      expect(getSessionMetadataRefetchInterval(metadata)).toBe(false);
    },
  );

  it("keeps polling after an initial request without metadata", () => {
    vi.spyOn(Math, "random").mockReturnValue(0.5);

    expect(getSessionMetadataRefetchInterval()).toBe(1000);
  });
});
