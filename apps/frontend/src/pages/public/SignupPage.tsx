import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Eye, EyeOff, Shield, User } from "lucide-react";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import {
  isEnrollmentApiEnabled,
  PENDING_ENROLLMENT_TOKEN_KEY,
} from "../../auth/enrollment";
import { useAuth } from "../../auth/useAuth";
import { useValidateClassCodeMutation } from "../../query/publicMutations";
import {
  type ConfirmSignupForm,
  confirmSignupSchema,
  type SignupForm,
  signupSchema,
} from "../../schemas/authForms";

type SignupInputProps = {
  id: string;
  label: string;
  placeholder: string;
  type?: "text" | "email" | "password";
  value: string;
  onChange: (value: string) => void;
  autoComplete?: string;
  rightSlot?: React.ReactNode;
};

function SignupInput({
  id,
  label,
  placeholder,
  type = "text",
  value,
  onChange,
  autoComplete,
  rightSlot,
}: SignupInputProps) {
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

export default function SignupPage() {
  const { signup, confirmSignup } = useAuth();
  const navigate = useNavigate();
  const validateClassCodeMutation = useValidateClassCodeMutation();

  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const signupForm = useForm<SignupForm>({
    resolver: zodResolver(signupSchema),
    defaultValues: { classCode: "", email: "", password: "" },
  });
  const confirmationForm = useForm<ConfirmSignupForm>({
    resolver: zodResolver(confirmSignupSchema),
    defaultValues: { email: "", confirmationCode: "" },
  });
  const classCode = useWatch({
    control: signupForm.control,
    name: "classCode",
  });
  const email = useWatch({ control: signupForm.control, name: "email" });
  const password = useWatch({ control: signupForm.control, name: "password" });
  const confirmationCode = useWatch({
    control: confirmationForm.control,
    name: "confirmationCode",
  });
  const validationError = awaitingConfirmation
    ? (confirmationForm.formState.errors.confirmationCode?.message ??
      confirmationForm.formState.errors.email?.message)
    : (signupForm.formState.errors.classCode?.message ??
      signupForm.formState.errors.email?.message ??
      signupForm.formState.errors.password?.message);
  const submitting =
    signupForm.formState.isSubmitting ||
    confirmationForm.formState.isSubmitting;

  const onSignup = async (values: SignupForm) => {
    setError(null);
    setSuccessMessage(null);
    validateClassCodeMutation.reset();
    try {
      if (isEnrollmentApiEnabled()) {
        const enrollmentToken = await validateClassCodeMutation.mutateAsync({
          classCode: values.classCode,
          email: values.email,
        });
        window.sessionStorage.setItem(
          PENDING_ENROLLMENT_TOKEN_KEY,
          enrollmentToken,
        );
      }

      await signup(values.email, values.password);
      confirmationForm.setValue("email", values.email);
      setAwaitingConfirmation(true);
      setSuccessMessage(
        "Account created. Enter the confirmation code from your email.",
      );
    } catch (signupError) {
      setError(
        signupError instanceof Error ? signupError.message : "Signup failed.",
      );
    }
  };

  const onConfirmSignup = async (values: ConfirmSignupForm) => {
    setError(null);
    setSuccessMessage(null);
    try {
      await confirmSignup(values.email, values.confirmationCode);
      setSuccessMessage("Email confirmed. You can now log in.");
      window.setTimeout(() => {
        navigate("/login", { replace: true });
      }, 600);
    } catch (confirmError) {
      setError(
        confirmError instanceof Error
          ? confirmError.message
          : "Confirmation failed.",
      );
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
              <span style={{ color: "#ffffff" }}>Create your account</span>
              <span className="block text-lime-300 drop-shadow-[0_0_22px_rgba(132,204,22,0.45)]">
                Start the lab experience
              </span>
            </h1>
          </section>

          <section className="mx-auto w-full max-w-xl rounded-[2rem] border border-lime-400/50 bg-black/45 p-8 shadow-[0_0_46px_rgba(132,204,22,0.18)] backdrop-blur-md md:p-12">
            <h2
              className="mb-7 text-5xl font-black tracking-tight text-white md:text-6xl"
              style={{ color: "#ffffff" }}
            >
              Sign up
            </h2>

            <form
              className="space-y-6"
              onSubmit={
                awaitingConfirmation
                  ? confirmationForm.handleSubmit(onConfirmSignup)
                  : signupForm.handleSubmit(onSignup)
              }
            >
              {!awaitingConfirmation ? (
                <>
                  <SignupInput
                    id="signup-class-code"
                    label="Class Code"
                    placeholder="Enter class code"
                    value={classCode}
                    onChange={(value) =>
                      signupForm.setValue("classCode", value, {
                        shouldValidate: true,
                      })
                    }
                    autoComplete="off"
                  />
                  <SignupInput
                    id="signup-email"
                    type="email"
                    label="Email Address"
                    placeholder="you@example.edu"
                    value={email}
                    onChange={(value) =>
                      signupForm.setValue("email", value, {
                        shouldValidate: true,
                      })
                    }
                    autoComplete="email"
                  />
                  <SignupInput
                    id="signup-password"
                    type={showPassword ? "text" : "password"}
                    label="Password"
                    placeholder="Create a password"
                    value={password}
                    onChange={(value) =>
                      signupForm.setValue("password", value, {
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
              ) : (
                <SignupInput
                  id="signup-confirm-code"
                  label="Confirmation Code"
                  placeholder="Enter confirmation code"
                  value={confirmationCode}
                  onChange={(value) =>
                    confirmationForm.setValue("confirmationCode", value, {
                      shouldValidate: true,
                    })
                  }
                  autoComplete="one-time-code"
                />
              )}

              {successMessage ? (
                <p className="text-sm text-emerald-300">{successMessage}</p>
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
                  : awaitingConfirmation
                    ? "Confirm Email"
                    : "Create Account"}
                <ArrowRight className="h-5 w-5 transition group-hover:translate-x-1" />
              </button>
            </form>

            <div className="my-8 h-px bg-lime-500/15" />

            <p className="text-sm text-slate-400">
              Already have an account?{" "}
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
