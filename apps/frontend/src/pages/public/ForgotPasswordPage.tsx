import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Eye, EyeOff, Shield, User } from "lucide-react";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { useAuth } from "../../auth/useAuth";
import {
  type PasswordResetConfirmationForm,
  type PasswordResetRequestForm,
  passwordResetConfirmationSchema,
  passwordResetRequestSchema,
} from "../../schemas/authForms";

type ResetInputProps = {
  id: string;
  label: string;
  placeholder: string;
  type?: "text" | "email" | "password";
  value: string;
  onChange: (value: string) => void;
  autoComplete?: string;
  rightSlot?: React.ReactNode;
};

function ResetInput({
  id,
  label,
  placeholder,
  type = "text",
  value,
  onChange,
  autoComplete,
  rightSlot,
}: ResetInputProps) {
  return (
    <label className="block" htmlFor={id}>
      <span className="mb-2 block text-sm font-bold text-slate-100">
        {label}
      </span>
      <div className="flex h-14 items-center rounded-lg border border-lime-400/80 bg-black/40 px-4 shadow-[0_0_18px_rgba(132,204,22,0.25)] transition">
        <input
          id={id}
          type={type}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          autoComplete={autoComplete}
          className="h-full min-w-0 flex-1 bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500"
        />
        {rightSlot ?? <User className="h-5 w-5 text-slate-300" />}
      </div>
    </label>
  );
}

export default function ForgotPasswordPage() {
  const { requestPasswordReset, confirmPasswordReset } = useAuth();
  const navigate = useNavigate();

  const [showPassword, setShowPassword] = useState(false);
  const [step, setStep] = useState<"request" | "confirm">("request");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const requestForm = useForm<PasswordResetRequestForm>({
    resolver: zodResolver(passwordResetRequestSchema),
    defaultValues: { email: "" },
  });
  const confirmationForm = useForm<PasswordResetConfirmationForm>({
    resolver: zodResolver(passwordResetConfirmationSchema),
    defaultValues: { email: "", code: "", newPassword: "" },
  });
  const requestEmail = useWatch({
    control: requestForm.control,
    name: "email",
  });
  const confirmationEmail = useWatch({
    control: confirmationForm.control,
    name: "email",
  });
  const email = step === "request" ? requestEmail : confirmationEmail;
  const code = useWatch({ control: confirmationForm.control, name: "code" });
  const newPassword = useWatch({
    control: confirmationForm.control,
    name: "newPassword",
  });
  const validationError =
    step === "request"
      ? requestForm.formState.errors.email?.message
      : (confirmationForm.formState.errors.email?.message ??
        confirmationForm.formState.errors.code?.message ??
        confirmationForm.formState.errors.newPassword?.message);
  const submitting =
    requestForm.formState.isSubmitting ||
    confirmationForm.formState.isSubmitting;

  const onRequest = async (values: PasswordResetRequestForm) => {
    setError(null);
    setMessage(null);
    try {
      await requestPasswordReset(values.email);
      confirmationForm.setValue("email", values.email);
      setStep("confirm");
      setMessage("Reset code sent. Check your email.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reset request failed.");
    }
  };

  const onConfirm = async (values: PasswordResetConfirmationForm) => {
    setError(null);
    setMessage(null);
    try {
      await confirmPasswordReset(values.email, values.code, values.newPassword);
      setMessage("Password updated. Redirecting to login.");
      window.setTimeout(() => navigate("/login", { replace: true }), 700);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Password reset failed.");
    }
  };

  return (
    <div className="min-h-screen overflow-hidden bg-black text-slate-100">
      <div className="relative min-h-screen">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_25%_30%,rgba(132,204,22,0.15),transparent_30%),radial-gradient(circle_at_80%_45%,rgba(34,197,94,0.14),transparent_28%),linear-gradient(180deg,#020617_0%,#020617_42%,#000_100%)]" />

        <main className="relative z-10 mx-auto grid min-h-screen max-w-7xl grid-cols-1 items-center gap-12 px-6 py-12 md:px-10 lg:grid-cols-[1fr_0.95fr]">
          <section className="max-w-2xl">
            <div className="mb-16 flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-lime-500/15 text-lime-300 ring-1 ring-lime-400/40 shadow-[0_0_34px_rgba(132,204,22,0.35)]">
                <Shield className="h-10 w-10" />
              </div>
              <span className="text-3xl font-extrabold tracking-tight text-white">
                Agent Failure
              </span>
            </div>

            <h1 className="text-5xl font-black leading-tight tracking-tight text-white md:text-6xl">
              <span style={{ color: "#ffffff" }}>Reset your password</span>
              <span className="block text-lime-300 drop-shadow-[0_0_22px_rgba(132,204,22,0.45)]">
                Recover account access
              </span>
            </h1>
          </section>

          <section className="mx-auto w-full max-w-xl rounded-[2rem] border border-lime-400/50 bg-black/45 p-8 shadow-[0_0_46px_rgba(132,204,22,0.18)] backdrop-blur-md md:p-12">
            <h2
              className="mb-7 text-5xl font-black tracking-tight text-white md:text-6xl"
              style={{ color: "#ffffff" }}
            >
              {step === "request" ? "Forgot Password" : "Confirm Reset"}
            </h2>

            <form
              className="space-y-6"
              onSubmit={
                step === "request"
                  ? requestForm.handleSubmit(onRequest)
                  : confirmationForm.handleSubmit(onConfirm)
              }
            >
              <ResetInput
                id="reset-email"
                type="email"
                label="Email Address"
                placeholder="you@example.edu"
                value={email}
                onChange={(value) => {
                  if (step === "request") {
                    requestForm.setValue("email", value, {
                      shouldValidate: true,
                    });
                  } else {
                    confirmationForm.setValue("email", value, {
                      shouldValidate: true,
                    });
                  }
                }}
                autoComplete="email"
              />

              {step === "confirm" ? (
                <>
                  <ResetInput
                    id="reset-code"
                    label="Verification Code"
                    placeholder="Enter verification code"
                    value={code}
                    onChange={(value) =>
                      confirmationForm.setValue("code", value, {
                        shouldValidate: true,
                      })
                    }
                    autoComplete="one-time-code"
                  />
                  <ResetInput
                    id="reset-password"
                    type={showPassword ? "text" : "password"}
                    label="New Password"
                    placeholder="Enter new password"
                    value={newPassword}
                    onChange={(value) =>
                      confirmationForm.setValue("newPassword", value, {
                        shouldValidate: true,
                      })
                    }
                    autoComplete="new-password"
                    rightSlot={
                      <button
                        type="button"
                        onClick={() => setShowPassword((prev) => !prev)}
                        aria-label={
                          showPassword ? "Hide password" : "Show password"
                        }
                        className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-300 transition hover:bg-lime-500/10 hover:text-lime-200"
                      >
                        {showPassword ? (
                          <EyeOff className="h-5 w-5" />
                        ) : (
                          <Eye className="h-5 w-5" />
                        )}
                      </button>
                    }
                  />
                </>
              ) : null}

              {message ? (
                <p className="text-sm text-emerald-300">{message}</p>
              ) : null}
              {error || validationError ? (
                <p className="text-sm text-rose-300">
                  {error ?? validationError}
                </p>
              ) : null}

              <button
                type="submit"
                disabled={submitting}
                className="group flex h-16 w-full items-center justify-center gap-3 rounded-lg bg-lime-300 text-base font-black text-black shadow-[0_0_28px_rgba(132,204,22,0.55)] transition hover:bg-lime-200 hover:shadow-[0_0_42px_rgba(132,204,22,0.75)] disabled:cursor-not-allowed disabled:opacity-70"
              >
                {submitting
                  ? "Submitting..."
                  : step === "request"
                    ? "Send Reset Code"
                    : "Update Password"}
                <ArrowRight className="h-5 w-5 transition group-hover:translate-x-1" />
              </button>
            </form>

            <div className="my-8 h-px bg-lime-500/15" />

            <p className="text-sm text-slate-400">
              Remembered your password?{" "}
              <Link
                to="/login#already-have-account"
                className="font-semibold text-lime-300 transition hover:text-lime-200"
              >
                Log in
              </Link>
            </p>
          </section>
        </main>
      </div>
    </div>
  );
}
