import { describe, expect, it } from "vitest";
import {
  getLabGuideContent,
  getLabGuideContentByLookup,
} from "./labGuideContent";

describe("getLabGuideContent", () => {
  it("returns agent lab 1 copy for agent prompt injection id", () => {
    const content = getLabGuideContent("44444444-4444-4444-4444-444444444444");
    expect(content.title).toBe("Indirect Prompt Injection");
    expect(content.objective).toContain("target information");
    expect(content.attackVector).toBe("Email inbox");
    expect(content.evidence[0]).toContain("Malicious email");
  });

  it("returns agent lab 2 tool misuse copy for lab 2 id", () => {
    const content = getLabGuideContent("55555555-5555-5555-5555-555555555555");
    expect(content.title).toBe("Tool Misuse");
    expect(content.successCriteria[2]).toBe(
      "Delete the protected critical file.",
    );
  });

  it("returns agent lab 3 memory poisoning copy for lab 3 id", () => {
    const content = getLabGuideContent("66666666-6666-6666-6666-666666666666");
    expect(content.title).toBe("Agent: Memory Poisoning");
    expect(content.missionOverview).toContain("attacker-controlled");
    expect(content.successCriteria[2]).toBe(
      "Route pay_invoice to the attacker account instead of the canonical account.",
    );
  });

  it("returns agent lab 3 memory poisoning copy for lab 3 slug/version", () => {
    const content = getLabGuideContentByLookup({
      labSlug: "agent-memory-poisoning",
      labVersion: "v1",
    });
    expect(content.title).toBe("Agent: Memory Poisoning");
    expect(content.successCriteria[1]).toContain("retrieved");
  });

  it("falls back to default copy for unknown lab ids", () => {
    const content = getLabGuideContent("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    expect(content.title).toBe("Indirect Prompt Injection: Poisoned Inbox");
  });
});
