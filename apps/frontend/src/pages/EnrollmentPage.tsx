import { ArrowRight, KeyRound, Shield, User } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  clearEnrollmentRedeemError,
  clearPendingEnrollmentToken,
  getEnrollmentRedeemError,
  PENDING_ENROLLMENT_TOKEN_KEY,
} from "../auth/enrollment";
import { useAuth } from "../auth/useAuth";
import {
  useRedeemEnrollmentMutation,
  useValidateClassCodeMutation,
} from "../query/publicMutations";

function getErrorMessage(error: unknown): string | null {
  if (!error) return null;
  return error instanceof Error
    ? error.message
    : "Enrollment failed. Please try again.";
}

export default function EnrollmentPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const validateClassCodeMutation = useValidateClassCodeMutation();
  const redeemEnrollmentMutation = useRedeemEnrollmentMutation();

  const [classCode, setClassCode] = useState("");
  const [localError, setLocalError] = useState<string | null>(
    getEnrollmentRedeemError(),
  );
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const submitting =
    validateClassCodeMutation.isPending || redeemEnrollmentMutation.isPending;
  const error =
    localError ??
    getErrorMessage(redeemEnrollmentMutation.error) ??
    getErrorMessage(validateClassCodeMutation.error);

  const onValidateAndEnroll = async () => {
    const email = user?.email?.trim() ?? "";
    if (!email) {
      setLocalError("Authenticated user email is missing.");
      return;
    }

    if (!classCode.trim()) {
      setLocalError("Class code is required.");
      return;
    }

    setLocalError(null);
    setSuccessMessage(null);
    validateClassCodeMutation.reset();
    redeemEnrollmentMutation.reset();

    try {
      const token = await validateClassCodeMutation.mutateAsync({
        classCode,
        email,
      });
      window.sessionStorage.setItem(PENDING_ENROLLMENT_TOKEN_KEY, token);
      await redeemEnrollmentMutation.mutateAsync(token);
      window.sessionStorage.removeItem(PENDING_ENROLLMENT_TOKEN_KEY);
      clearEnrollmentRedeemError();
      setSuccessMessage("Enrollment complete. Redirecting to lab catalog.");
      window.setTimeout(() => {
        navigate("/labs", { replace: true });
      }, 500);
    } catch {
      // The mutation that failed owns the error displayed above.
    }
  };

  const showRecoveryHelp =
    error === "Enrollment token email does not match authenticated user" ||
    error === "Token expired or already redeemed" ||
    error === "Enrollment token redemption failed.";

  return (
    <div className="min-h-[calc(100vh-96px)] px-6 py-8 md:px-10">
      <section className="mx-auto w-full max-w-2xl rounded-2xl border border-lime-400/40 bg-black/50 p-7 text-slate-100 shadow-[0_0_40px_rgba(132,204,22,0.14)] backdrop-blur-md md:p-10">
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-xl bg-lime-500/15 p-2.5 text-lime-300 ring-1 ring-lime-400/40">
            <Shield className="h-5 w-5" />
          </div>
          <h1
            className="text-2xl font-black tracking-tight text-white md:text-3xl"
            style={{ color: "#ffffff" }}
          >
            Complete Course Enrollment
          </h1>
        </div>

        <p className="mb-6 text-sm leading-6 text-slate-300">
          Your account is authenticated. Enter your class code to enroll and
          continue to the lab catalog.
        </p>

        <div className="space-y-5">
          <label className="block" htmlFor="enrollment-email">
            <span className="mb-2 block text-sm font-bold text-slate-200">
              Signed in as
            </span>
            <div className="flex h-12 items-center gap-2 rounded-lg border border-slate-600/70 bg-slate-900/60 px-4 text-sm text-slate-200">
              <User className="h-4 w-4 text-slate-400" />
              <span>{user?.email ?? "Unknown user"}</span>
            </div>
          </label>

          <label className="block" htmlFor="enrollment-class-code">
            <span className="mb-2 block text-sm font-bold text-slate-200">
              Class Code
            </span>
            <div className="flex h-12 items-center gap-2 rounded-lg border border-lime-400/70 bg-black/40 px-4 shadow-[0_0_16px_rgba(132,204,22,0.2)]">
              <KeyRound className="h-4 w-4 text-lime-300" />
              <input
                id="enrollment-class-code"
                value={classCode}
                onChange={(event) => setClassCode(event.target.value)}
                placeholder="Enter class code"
                autoComplete="off"
                className="h-full min-w-0 flex-1 bg-transparent text-sm text-slate-100 outline-none placeholder:text-slate-500"
              />
            </div>
          </label>

          {successMessage ? (
            <p className="text-sm text-emerald-300">{successMessage}</p>
          ) : null}
          {error ? <p className="text-sm text-rose-300">{error}</p> : null}
          {showRecoveryHelp ? (
            <div className="rounded-lg border border-amber-400/40 bg-amber-950/20 p-3 text-sm text-amber-200">
              <p>
                Your previous enrollment link is no longer valid. Enter a class
                code again to continue.
              </p>
              <button
                type="button"
                className="mt-2 text-xs font-semibold text-amber-100 underline underline-offset-2 hover:text-white"
                onClick={() => {
                  clearPendingEnrollmentToken();
                  clearEnrollmentRedeemError();
                  validateClassCodeMutation.reset();
                  redeemEnrollmentMutation.reset();
                  setLocalError(null);
                  setSuccessMessage(null);
                  setClassCode("");
                }}
              >
                Enter a new class code
              </button>
            </div>
          ) : null}

          <button
            type="button"
            onClick={() => {
              void onValidateAndEnroll();
            }}
            disabled={submitting}
            className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-lime-300 px-4 text-sm font-black text-black shadow-[0_0_28px_rgba(132,204,22,0.45)] transition hover:bg-lime-200 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {submitting ? "Validating..." : "Validate and Enroll"}
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </section>
    </div>
  );
}
