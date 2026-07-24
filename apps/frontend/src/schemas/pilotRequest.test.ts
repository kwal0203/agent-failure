import { describe, expect, it } from "vitest";
import { pilotLeadSchema } from "./pilotRequest";

describe("pilotLeadSchema", () => {
  it("normalizes submitted lead data and removes blank optional fields", () => {
    expect(
      pilotLeadSchema.parse({
        fullName: "  Jane Smith  ",
        workEmail: "  JANE@EXAMPLE.EDU  ",
        university: "  Example University  ",
        courseName: "   ",
        notes: "",
      }),
    ).toEqual({
      fullName: "Jane Smith",
      workEmail: "jane@example.edu",
      university: "Example University",
    });
  });

  it("enforces field limits at the shared trust boundary", () => {
    const result = pilotLeadSchema.safeParse({
      fullName: "Jane Smith",
      workEmail: "jane@example.edu",
      university: "Example University",
      cohortSize: 100_001,
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.message).toBe(
        "Cohort size must be a positive integer.",
      );
    }
  });
});
