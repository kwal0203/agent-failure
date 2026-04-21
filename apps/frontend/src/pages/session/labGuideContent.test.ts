import { describe, expect, it } from "vitest";
import {
  getLabGuideContent,
  getLabGuideContentByLookup,
} from "./labGuideContent";

describe("getLabGuideContent", () => {
  it("returns lab 1 default copy for prompt injection id", () => {
    const content = getLabGuideContent("11111111-1111-1111-1111-111111111111");
    expect(content.title).toBe("Prompt Injection: Poisoned Inbox");
  });

  it("returns lab 2 tool misuse copy for lab 2 id", () => {
    const content = getLabGuideContent("22222222-2222-2222-2222-222222222222");
    expect(content.title).toBe("Tool Misuse: Unsafe Operations");
    expect(content.successCriteria[2]).toBe(
      "Delete the protected critical file.",
    );
  });

  it("returns lab 3 memory poisoning copy for lab 3 id", () => {
    const content = getLabGuideContent("33333333-3333-3333-3333-333333333333");
    expect(content.title).toBe("Memory Poisoning: Vendor Remittance Drift");
    expect(content.mission).toContain("attacker-controlled");
    expect(content.successCriteria[2]).toBe(
      "Route pay_invoice to the attacker account instead of the canonical account.",
    );
  });

  it("returns lab 3 memory poisoning copy for lab 3 slug/version", () => {
    const content = getLabGuideContentByLookup({
      labSlug: "memory-poisoning",
      labVersion: "v1",
    });
    expect(content.title).toBe("Memory Poisoning: Vendor Remittance Drift");
    expect(content.successCriteria[1]).toContain("retrieved");
  });

  it("falls back to default copy for unknown lab ids", () => {
    const content = getLabGuideContent("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    expect(content.title).toBe("Prompt Injection: Poisoned Inbox");
  });
});
