import { describe, expect, it } from "vitest";
import { getLabGuideContent } from "./labGuideContent";

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

  it("falls back to default copy for unknown lab ids", () => {
    const content = getLabGuideContent("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    expect(content.title).toBe("Prompt Injection: Poisoned Inbox");
  });
});
