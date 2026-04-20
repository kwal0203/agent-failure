import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const AUTH_STORAGE_KEY = "agent_failure_auth_user";
const AUTH_ACCOUNTS_STORAGE_KEY = "agent_failure_auth_accounts";

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
  login: (email: string, _password: string) => Promise<void>;
  signup: (email: string, _password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredUser(): AuthUser | null {
  const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;

  try {
    const parsed = JSON.parse(raw) as AuthUser;
    if (!parsed?.id || !parsed?.email) return null;
    return parsed;
  } catch {
    return null;
  }
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
    id: "kane@example.com",
    email: "kane@example.com",
    label: "kane",
    password: "password123",
  },
];

function normalizeIdentifier(value: string): string {
  return value.trim().toLowerCase();
}

function readStoredAccounts(): StoredAuthAccount[] {
  const raw = window.localStorage.getItem(AUTH_ACCOUNTS_STORAGE_KEY);
  if (!raw) return DEFAULT_ACCOUNTS;

  try {
    const parsed = JSON.parse(raw) as StoredAuthAccount[];
    if (!Array.isArray(parsed)) return DEFAULT_ACCOUNTS;
    return parsed.filter(
      (item) =>
        typeof item?.id === "string" &&
        typeof item?.email === "string" &&
        typeof item?.label === "string" &&
        typeof item?.password === "string",
    );
  } catch {
    return DEFAULT_ACCOUNTS;
  }
}

function persistAccounts(accounts: StoredAuthAccount[]) {
  window.localStorage.setItem(
    AUTH_ACCOUNTS_STORAGE_KEY,
    JSON.stringify(accounts),
  );
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  useEffect(() => {
    const stored = readStoredUser();
    setUser(stored);
    setIsBootstrapping(false);
  }, []);

  const persistUser = useCallback((nextUser: AuthUser) => {
    setUser(nextUser);
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(nextUser));
  }, []);

  const login = useCallback(
    async (identifier: string, password: string) => {
      const normalized = normalizeIdentifier(identifier);
      const accounts = readStoredAccounts();
      const account = accounts.find(
        (item) =>
          item.id === normalized ||
          normalizeIdentifier(item.email) === normalized ||
          normalizeIdentifier(item.label) === normalized,
      );

      if (!account || account.password !== password) {
        throw new Error("Invalid credentials");
      }

      persistUser({
        id: account.id,
        email: account.email,
        label: account.label,
      });
    },
    [persistUser],
  );

  const signup = useCallback(
    async (email: string, password: string) => {
      const nextUser = buildUser(email.trim());
      const accounts = readStoredAccounts();
      const exists = accounts.some(
        (item) =>
          item.id === nextUser.id ||
          normalizeIdentifier(item.email) === nextUser.id,
      );
      if (exists) {
        throw new Error("Account already exists");
      }

      persistAccounts([
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
    [persistUser],
  );

  const logout = useCallback(() => {
    setUser(null);
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isBootstrapping,
      login,
      signup,
      logout,
    }),
    [isBootstrapping, login, logout, signup, user],
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
