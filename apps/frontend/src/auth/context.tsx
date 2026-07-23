import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  confirmPasswordResetWithAmplify,
  confirmSignUpWithAmplify,
  getAmplifySession,
  getAmplifyUser,
  requestPasswordResetWithAmplify,
  signInWithAmplify,
  signOutWithAmplify,
  signUpWithAmplify,
} from "./amplifyAuth";
import {
  AuthContext,
  type AuthContextValue,
  type AuthUser,
} from "./authContext";
import { tryRedeemPendingEnrollmentToken } from "./enrollment";
import { POST_LOGIN_REDIRECT_KEY } from "./redirect";

function stringClaim(payload: Record<string, unknown>, key: string): string {
  const value = payload[key];
  return typeof value === "string" ? value.trim() : "";
}

function stringArrayClaim(
  payload: Record<string, unknown>,
  key: string,
): string[] {
  const value = payload[key];
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter(
    (item): item is string =>
      typeof item === "string" && item.trim().length > 0,
  );
}

async function loadAuthenticatedUser(): Promise<AuthUser> {
  const amplifyUser = await getAmplifyUser();
  const session = await getAmplifySession();
  const payload = (session.tokens?.idToken?.payload ?? {}) as Record<
    string,
    unknown
  >;
  const email =
    stringClaim(payload, "email") ||
    amplifyUser.signInDetails?.loginId?.trim() ||
    "";
  const username =
    stringClaim(payload, "cognito:username") || amplifyUser.username.trim();
  const name = stringClaim(payload, "name");
  const preferredUsername = stringClaim(payload, "preferred_username");
  const label =
    name || preferredUsername || email.split("@")[0]?.trim() || username;

  if (!amplifyUser.userId.trim() || !email || !label) {
    throw new Error("Authenticated user is missing required identity claims.");
  }

  return {
    id: amplifyUser.userId.trim(),
    email,
    label,
    name: name || undefined,
    username: username || undefined,
    groups: stringArrayClaim(payload, "cognito:groups"),
  };
}

function unsupportedSignInStepMessage(signInStep: string): string {
  switch (signInStep) {
    case "CONFIRM_SIGN_UP":
      return "Confirm your email address before signing in.";
    case "RESET_PASSWORD":
      return "Your password must be reset before signing in.";
    default:
      return `Additional authentication is required (${signInStep}).`;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isAuthTransitioning, setIsAuthTransitioning] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const bootstrap = async () => {
      setIsAuthTransitioning(true);
      try {
        const authenticatedUser = await loadAuthenticatedUser();
        if (cancelled) return;
        setUser(authenticatedUser);
        await tryRedeemPendingEnrollmentToken();
      } catch {
        if (!cancelled) {
          setUser(null);
        }
      } finally {
        if (!cancelled) {
          setIsAuthTransitioning(false);
          setIsBootstrapping(false);
        }
      }
    };

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const normalizedEmail = email.trim().toLowerCase();
    const result = await signInWithAmplify(normalizedEmail, password);
    if (!result.isSignedIn) {
      throw new Error(unsupportedSignInStepMessage(result.nextStep.signInStep));
    }

    const authenticatedUser = await loadAuthenticatedUser();
    setUser(authenticatedUser);

    setIsAuthTransitioning(true);
    try {
      await tryRedeemPendingEnrollmentToken();
    } finally {
      setIsAuthTransitioning(false);
    }
  }, []);

  const signup = useCallback(async (email: string, password: string) => {
    const normalizedEmail = email.trim().toLowerCase();
    await signUpWithAmplify(normalizedEmail, password);
  }, []);

  const confirmSignup = useCallback(async (email: string, code: string) => {
    const normalizedEmail = email.trim().toLowerCase();
    const result = await confirmSignUpWithAmplify(normalizedEmail, code.trim());
    if (!result.isSignUpComplete) {
      throw new Error(
        `Additional signup verification is required (${result.nextStep.signUpStep}).`,
      );
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await signOutWithAmplify();
    } finally {
      setUser(null);
      window.sessionStorage.removeItem(POST_LOGIN_REDIRECT_KEY);
    }
  }, []);

  const requestPasswordReset = useCallback(async (email: string) => {
    const normalizedEmail = email.trim().toLowerCase();
    await requestPasswordResetWithAmplify(normalizedEmail);
  }, []);

  const confirmPasswordReset = useCallback(
    async (email: string, code: string, newPassword: string) => {
      const normalizedEmail = email.trim().toLowerCase();
      await confirmPasswordResetWithAmplify(
        normalizedEmail,
        code.trim(),
        newPassword,
      );
    },
    [],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isBootstrapping,
      isAuthTransitioning,
      login,
      signup,
      confirmSignup,
      requestPasswordReset,
      confirmPasswordReset,
      logout,
    }),
    [
      confirmPasswordReset,
      confirmSignup,
      isAuthTransitioning,
      isBootstrapping,
      login,
      logout,
      requestPasswordReset,
      signup,
      user,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
