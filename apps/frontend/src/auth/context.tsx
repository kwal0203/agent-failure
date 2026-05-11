import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { tryRedeemPendingEnrollmentToken } from "./enrollment";

export type AuthUser = {
  id: string;
  email: string;
  label: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  isAuthTransitioning: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  confirmSignup: (email: string, code: string) => Promise<void>;
  requestPasswordReset: (email: string) => Promise<void>;
  confirmPasswordReset: (
    email: string,
    code: string,
    newPassword: string,
  ) => Promise<void>;
  logout: () => void;
};

type CognitoTokens = {
  accessToken: string;
  idToken: string;
  refreshToken: string | null;
  expiresAtEpochSec: number;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const AUTH_USER_STORAGE_KEY = "agentfailure.auth.user";
const AUTH_TOKEN_STORAGE_KEY = "agentfailure.auth.tokens";

const cognitoClientId = (import.meta.env.VITE_COGNITO_CLIENT_ID ?? "").trim();
const cognitoUserPoolId = (
  import.meta.env.VITE_COGNITO_USER_POOL_ID ?? ""
).trim();

let currentAccessToken = "";

function ensureCognitoConfigured(): void {
  if (!cognitoClientId || !cognitoUserPoolId) {
    throw new Error(
      "Cognito is not configured. Missing VITE_COGNITO_CLIENT_ID or VITE_COGNITO_USER_POOL_ID.",
    );
  }
}

function getCognitoRegion(): string {
  const region = cognitoUserPoolId.split("_")[0]?.trim();
  if (!region) {
    throw new Error(
      "VITE_COGNITO_USER_POOL_ID must be in '<region>_<poolId>' format.",
    );
  }
  return region;
}

function getCognitoIdpEndpoint(): string {
  return `https://cognito-idp.${getCognitoRegion()}.amazonaws.com/`;
}

function readStoredUser(): AuthUser | null {
  const raw = window.sessionStorage.getItem(AUTH_USER_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as AuthUser;
    if (!parsed?.email || !parsed?.id || !parsed?.label) return null;
    return parsed;
  } catch {
    return null;
  }
}

function readStoredTokens(): CognitoTokens | null {
  const raw = window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as CognitoTokens;
    if (
      !parsed?.accessToken ||
      !parsed?.idToken ||
      !parsed?.expiresAtEpochSec
    ) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function decodeJwtPayload(token: string): Record<string, unknown> {
  const parts = token.split(".");
  if (parts.length < 2) {
    throw new Error("Invalid token format");
  }
  const payloadBase64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
  const payloadJson = atob(payloadBase64);
  return JSON.parse(payloadJson) as Record<string, unknown>;
}

function toAuthUserFromIdToken(idToken: string): AuthUser {
  const payload = decodeJwtPayload(idToken);
  const sub = typeof payload.sub === "string" ? payload.sub : "";
  const email = typeof payload.email === "string" ? payload.email : "";
  const preferredUsername =
    typeof payload.preferred_username === "string"
      ? payload.preferred_username
      : "";

  if (!sub || !email) {
    throw new Error("Missing required user claims in token");
  }

  const label = preferredUsername || email.split("@")[0] || email;
  return { id: sub, email, label };
}

function isTokenExpired(expiresAtEpochSec: number): boolean {
  const nowEpochSec = Math.floor(Date.now() / 1000);
  return expiresAtEpochSec <= nowEpochSec + 30;
}

type CognitoAuthResult = {
  AccessToken?: string;
  IdToken?: string;
  RefreshToken?: string;
  ExpiresIn?: number;
};

async function cognitoJsonRequest<T>(target: string, body: object): Promise<T> {
  ensureCognitoConfigured();

  const response = await fetch(getCognitoIdpEndpoint(), {
    method: "POST",
    headers: {
      "Content-Type": "application/x-amz-json-1.1",
      "X-Amz-Target": target,
    },
    body: JSON.stringify(body),
  });

  const text = await response.text();
  const parsed = text ? (JSON.parse(text) as Record<string, unknown>) : {};

  if (!response.ok) {
    const message =
      typeof parsed.message === "string"
        ? parsed.message
        : "Cognito request failed";
    throw new Error(message);
  }

  return parsed as T;
}

async function cognitoLogin(
  email: string,
  password: string,
): Promise<CognitoTokens> {
  const payload = await cognitoJsonRequest<{
    AuthenticationResult?: CognitoAuthResult;
  }>("AWSCognitoIdentityProviderService.InitiateAuth", {
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: cognitoClientId,
    AuthParameters: {
      USERNAME: email,
      PASSWORD: password,
    },
  });

  const auth = payload.AuthenticationResult;
  if (!auth?.AccessToken || !auth?.IdToken || !auth.ExpiresIn) {
    throw new Error("Authentication result is missing required tokens.");
  }

  return {
    accessToken: auth.AccessToken,
    idToken: auth.IdToken,
    refreshToken: auth.RefreshToken ?? null,
    expiresAtEpochSec: Math.floor(Date.now() / 1000) + auth.ExpiresIn,
  };
}

async function cognitoSignup(email: string, password: string): Promise<void> {
  await cognitoJsonRequest("AWSCognitoIdentityProviderService.SignUp", {
    ClientId: cognitoClientId,
    Username: email,
    Password: password,
    UserAttributes: [{ Name: "email", Value: email }],
  });
}

async function cognitoConfirmSignup(
  email: string,
  code: string,
): Promise<void> {
  await cognitoJsonRequest("AWSCognitoIdentityProviderService.ConfirmSignUp", {
    ClientId: cognitoClientId,
    Username: email,
    ConfirmationCode: code,
  });
}

async function cognitoRequestPasswordReset(email: string): Promise<void> {
  await cognitoJsonRequest("AWSCognitoIdentityProviderService.ForgotPassword", {
    ClientId: cognitoClientId,
    Username: email,
  });
}

async function cognitoConfirmPasswordReset(
  email: string,
  code: string,
  newPassword: string,
): Promise<void> {
  await cognitoJsonRequest(
    "AWSCognitoIdentityProviderService.ConfirmForgotPassword",
    {
      ClientId: cognitoClientId,
      Username: email,
      ConfirmationCode: code,
      Password: newPassword,
    },
  );
}

export function getCurrentAccessToken(): string {
  return currentAccessToken;
}

export function getCurrentAuthHeader(): string {
  if (!currentAccessToken) {
    throw new Error("No active access token. User must be authenticated.");
  }
  return `Bearer ${currentAccessToken}`;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [tokens, setTokens] = useState<CognitoTokens | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [isAuthTransitioning, setIsAuthTransitioning] = useState(false);

  useEffect(() => {
    const bootstrap = async () => {
      setIsAuthTransitioning(true);
      try {
        ensureCognitoConfigured();
        const storedTokens = readStoredTokens();
        const storedUser = readStoredUser();

        if (
          storedTokens &&
          storedUser &&
          !isTokenExpired(storedTokens.expiresAtEpochSec)
        ) {
          setTokens(storedTokens);
          setUser(storedUser);
          currentAccessToken = storedTokens.accessToken;
          await tryRedeemPendingEnrollmentToken();
        } else {
          currentAccessToken = "";
          window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
          window.sessionStorage.removeItem(AUTH_USER_STORAGE_KEY);
        }
      } finally {
        setIsAuthTransitioning(false);
        setIsBootstrapping(false);
      }
    };

    void bootstrap();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const normalizedEmail = email.trim().toLowerCase();
    const authTokens = await cognitoLogin(normalizedEmail, password);
    const nextUser = toAuthUserFromIdToken(authTokens.idToken);

    setTokens(authTokens);
    setUser(nextUser);
    currentAccessToken = authTokens.accessToken;

    window.sessionStorage.setItem(
      AUTH_TOKEN_STORAGE_KEY,
      JSON.stringify(authTokens),
    );
    window.sessionStorage.setItem(
      AUTH_USER_STORAGE_KEY,
      JSON.stringify(nextUser),
    );

    setIsAuthTransitioning(true);
    try {
      await tryRedeemPendingEnrollmentToken();
    } finally {
      setIsAuthTransitioning(false);
    }
  }, []);

  const signup = useCallback(async (email: string, password: string) => {
    const normalizedEmail = email.trim().toLowerCase();
    await cognitoSignup(normalizedEmail, password);
  }, []);

  const confirmSignup = useCallback(async (email: string, code: string) => {
    const normalizedEmail = email.trim().toLowerCase();
    await cognitoConfirmSignup(normalizedEmail, code.trim());
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    setTokens(null);
    currentAccessToken = "";
    window.sessionStorage.removeItem(AUTH_USER_STORAGE_KEY);
    window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  }, []);

  const requestPasswordReset = useCallback(async (email: string) => {
    const normalizedEmail = email.trim().toLowerCase();
    await cognitoRequestPasswordReset(normalizedEmail);
  }, []);

  const confirmPasswordReset = useCallback(
    async (email: string, code: string, newPassword: string) => {
      const normalizedEmail = email.trim().toLowerCase();
      await cognitoConfirmPasswordReset(
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
      isAuthenticated: Boolean(
        user && tokens && !isTokenExpired(tokens.expiresAtEpochSec),
      ),
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
      tokens,
      user,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
