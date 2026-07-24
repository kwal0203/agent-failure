import { z } from "zod";

const requiredEmail = z
  .string()
  .trim()
  .min(1, "Email is required.")
  .email("Enter a valid email address.");
const requiredPassword = z.string().min(1, "Password is required.");
const requiredCode = z.string().trim().min(1, "Confirmation code is required.");

export const loginSchema = z.object({
  email: requiredEmail,
  password: requiredPassword,
});

export const signupSchema = z.object({
  classCode: z.string().trim().min(1, "Class code is required."),
  email: requiredEmail,
  password: requiredPassword,
});

export const confirmSignupSchema = z.object({
  email: requiredEmail,
  confirmationCode: requiredCode,
});

export const passwordResetRequestSchema = z.object({
  email: requiredEmail,
});

export const passwordResetConfirmationSchema = z.object({
  email: requiredEmail,
  code: requiredCode,
  newPassword: z.string().min(1, "New password is required."),
});

export const enrollmentSchema = z.object({
  classCode: z.string().trim().min(1, "Class code is required."),
});

export const injectedEmailSchema = z.object({
  emailFrom: z
    .string()
    .trim()
    .min(1, "From is required.")
    .email("From must be a valid email address."),
  emailSubject: z.string().trim().min(1, "Subject is required."),
  emailBody: z.string().trim().min(1, "Body is required."),
});

export type LoginForm = z.infer<typeof loginSchema>;
export type SignupForm = z.infer<typeof signupSchema>;
export type ConfirmSignupForm = z.infer<typeof confirmSignupSchema>;
export type PasswordResetRequestForm = z.infer<
  typeof passwordResetRequestSchema
>;
export type PasswordResetConfirmationForm = z.infer<
  typeof passwordResetConfirmationSchema
>;
export type EnrollmentForm = z.infer<typeof enrollmentSchema>;
