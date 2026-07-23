import { z } from "zod";

function requiredText(label: string, maxLength: number) {
  return z
    .string({ error: `${label} must be a string.` })
    .trim()
    .min(1, `${label} is required.`)
    .max(maxLength, `${label} is too long.`);
}

function optionalText(label: string, maxLength: number) {
  return z
    .string({ error: `${label} must be a string.` })
    .trim()
    .max(maxLength, `${label} is too long.`)
    .optional();
}

export const pilotLeadSchema = z
  .object({
    fullName: requiredText("Full name", 120),
    workEmail: requiredText("Work email", 254).pipe(
      z.email("Enter a valid work email."),
    ),
    university: requiredText("University", 160),
    role: optionalText("Role", 120),
    courseName: optionalText("Course name", 160),
    cohortSize: z
      .number({ error: "Cohort size must be a positive integer." })
      .int("Cohort size must be a positive integer.")
      .min(1, "Cohort size must be a positive integer.")
      .max(100_000, "Cohort size must be a positive integer.")
      .optional(),
    notes: optionalText("Notes", 4_000),
    website: optionalText("Website", 500),
  })
  .transform((lead) => ({
    fullName: lead.fullName,
    workEmail: lead.workEmail.toLowerCase(),
    university: lead.university,
    ...(lead.role ? { role: lead.role } : {}),
    ...(lead.courseName ? { courseName: lead.courseName } : {}),
    ...(lead.cohortSize ? { cohortSize: lead.cohortSize } : {}),
    ...(lead.notes ? { notes: lead.notes } : {}),
    ...(lead.website ? { website: lead.website } : {}),
  }));

export type PilotLeadFormValues = z.input<typeof pilotLeadSchema>;
export type PilotLead = z.output<typeof pilotLeadSchema>;
