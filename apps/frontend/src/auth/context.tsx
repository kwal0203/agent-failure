import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

export type AuthUser = {
  id: string;
  email: string;
  label: string;
};

type StoredAuthAccount = {
  id: string;
  email: string;
  label: string;
  password: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const FALLBACK_DEMO_EMAIL = "kane@gatech.edu";
const AUTH_USER_STORAGE_KEY = "agentfailure.auth.user";
const AUTH_ACCOUNTS_STORAGE_KEY = "agentfailure.auth.accounts";
let currentAccessToken = `local:${FALLBACK_DEMO_EMAIL}:learner`;

function buildAccessToken(email: string): string {
  return `local:${email.trim().toLowerCase()}:learner`;
}

export function getCurrentAccessToken(): string {
  return currentAccessToken;
}

export function getCurrentAuthHeader(): string {
  return `Bearer ${currentAccessToken}`;
}

function buildUser(email: string): AuthUser {
  const normalized = email.toLowerCase().trim();
  return {
    id: normalized,
    email: email.trim(),
    label: email.trim().split("@")[0] || email.trim(),
  };
}

const DEFAULT_ACCOUNTS: StoredAuthAccount[] = [
  {
    id: "kane@gatech.edu",
    email: "kane@gatech.edu",
    label: "kane",
    password: "b73I2",
  },
];

function normalizeIdentifier(value: string): string {
  return value.trim().toLowerCase();
}

function isGeorgiaTechEmail(value: string): boolean {
  return /^[^@\s]+@gatech\.edu$/i.test(value.trim());
}

function readStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
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

function readStoredAccounts(): StoredAuthAccount[] {
  if (typeof window === "undefined") return DEFAULT_ACCOUNTS;
  const raw = window.sessionStorage.getItem(AUTH_ACCOUNTS_STORAGE_KEY);
  if (!raw) return DEFAULT_ACCOUNTS;
  try {
    const parsed = JSON.parse(raw) as StoredAuthAccount[];
    if (!Array.isArray(parsed)) return DEFAULT_ACCOUNTS;
    return parsed;
  } catch {
    return DEFAULT_ACCOUNTS;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser());
  const [accounts, setAccounts] = useState<StoredAuthAccount[]>(() =>
    readStoredAccounts(),
  );

  useEffect(() => {
    if (user) {
      currentAccessToken = buildAccessToken(user.email);
    } else {
      currentAccessToken = buildAccessToken(FALLBACK_DEMO_EMAIL);
    }
  }, [user]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (user) {
      window.sessionStorage.setItem(
        AUTH_USER_STORAGE_KEY,
        JSON.stringify(user),
      );
      return;
    }
    window.sessionStorage.removeItem(AUTH_USER_STORAGE_KEY);
  }, [user]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.sessionStorage.setItem(
      AUTH_ACCOUNTS_STORAGE_KEY,
      JSON.stringify(accounts),
    );
  }, [accounts]);

  const persistUser = useCallback((nextUser: AuthUser) => {
    setUser(nextUser);
    currentAccessToken = buildAccessToken(nextUser.email);
  }, []);

  const login = useCallback(
    async (identifier: string, password: string) => {
      if (!isGeorgiaTechEmail(identifier)) {
        throw new Error("Invalid credentials");
      }
      const normalized = normalizeIdentifier(identifier);
      const account = accounts.find(
        (item) =>
          item.id === normalized ||
          normalizeIdentifier(item.email) === normalized ||
          normalizeIdentifier(item.label) === normalized,
      );

      if (!password.trim()) {
        throw new Error("Password is required");
      }

      if (account) {
        if (account.password !== password) {
          throw new Error("Invalid credentials");
        }
        persistUser({
          id: account.id,
          email: account.email,
          label: account.label,
        });
        return;
      }

      const nextUser = buildUser(identifier.trim());
      setAccounts((prev) => [
        ...prev,
        {
          id: nextUser.id,
          email: nextUser.email,
          label: nextUser.label,
          password,
        },
      ]);
      persistUser(nextUser);
    },
    [accounts, persistUser],
  );

  const signup = useCallback(
    async (email: string, password: string) => {
      const nextUser = buildUser(email.trim());
      const exists = accounts.some(
        (item) =>
          item.id === nextUser.id ||
          normalizeIdentifier(item.email) === nextUser.id,
      );
      if (exists) {
        throw new Error("Account already exists");
      }

      setAccounts([
        ...accounts,
        {
          id: nextUser.id,
          email: nextUser.email,
          label: nextUser.label,
          password,
        },
      ]);
      persistUser(nextUser);
    },
    [accounts, persistUser],
  );

  const logout = useCallback(() => {
    setUser(null);
    currentAccessToken = buildAccessToken(FALLBACK_DEMO_EMAIL);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isBootstrapping: false,
      login,
      signup,
      logout,
    }),
    [login, logout, signup, user],
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
