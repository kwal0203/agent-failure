import {
  Bell,
  BookOpen,
  FileText,
  GraduationCap,
  LifeBuoy,
  Shield,
  Users,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/context";
import type { ShellBootstrap } from "../shell/context";

const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
  textDecoration: "none",
  color: isActive ? "#8bff8f" : "#9dc6a2",
  borderBottom: isActive ? "2px solid #2e7d32" : "2px solid transparent",
  padding: "8px 4px",
  fontWeight: isActive ? 700 : 500,
});

const rawUiMode = (import.meta.env.VITE_UI_MODE ?? "demo").toLowerCase();
const uiMode: ShellBootstrap["mode"] = rawUiMode === "debug" ? "debug" : "demo";

const bootstrap: ShellBootstrap = {
  mode: uiMode,
  learnerLabel: "Demo Learner",
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
};

const catalogNavItems = [
  { label: "Catalog", icon: BookOpen, to: "/labs" },
  { label: "Courses", icon: GraduationCap, to: null },
  { label: "Reports", icon: FileText, to: "/reports" },
];

const resourceItems = [
  { label: "Standards", icon: Shield },
  { label: "Documentation", icon: FileText },
  { label: "Community", icon: Users },
  { label: "Support", icon: LifeBuoy },
];

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(payload)) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function canViewPilotRequests(): boolean {
  const rawTokens = window.sessionStorage.getItem("agentfailure.auth.tokens");
  if (!rawTokens) return false;
  try {
    const parsed = JSON.parse(rawTokens) as { idToken?: string };
    if (!parsed.idToken) return false;
    const payload = decodeJwtPayload(parsed.idToken);
    const groups = payload?.["cognito:groups"];
    if (!Array.isArray(groups)) return false;
    return groups.includes("admin") || groups.includes("staff");
  } catch {
    return false;
  }
}

type ViewerProfile = {
  displayName: string;
  initials: string;
  roleLabel: string;
};

function deriveViewerProfile(): ViewerProfile {
  const defaultProfile: ViewerProfile = {
    displayName: "User",
    initials: "US",
    roleLabel: "Student",
  };
  const rawTokens = window.sessionStorage.getItem("agentfailure.auth.tokens");
  if (!rawTokens) return defaultProfile;

  try {
    const parsed = JSON.parse(rawTokens) as { idToken?: string };
    if (!parsed.idToken) return defaultProfile;
    const payload = decodeJwtPayload(parsed.idToken);
    if (!payload) return defaultProfile;

    const name = typeof payload.name === "string" ? payload.name.trim() : "";
    const email = typeof payload.email === "string" ? payload.email.trim() : "";
    const username =
      typeof payload["cognito:username"] === "string"
        ? payload["cognito:username"].trim()
        : "";
    const groups = Array.isArray(payload["cognito:groups"])
      ? payload["cognito:groups"].filter(
          (value): value is string => typeof value === "string",
        )
      : [];

    const displayName =
      name ||
      email.split("@")[0]?.trim() ||
      username ||
      defaultProfile.displayName;
    const initials = displayName
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("")
      .slice(0, 2);

    const normalizedGroups = groups.map((group) => group.toLowerCase());
    const roleLabel = normalizedGroups.includes("admin")
      ? "Admin"
      : normalizedGroups.includes("staff") ||
          normalizedGroups.includes("instructor")
        ? "Instructor"
        : defaultProfile.roleLabel;

    return {
      displayName,
      initials: initials || defaultProfile.initials,
      roleLabel,
    };
  } catch {
    return defaultProfile;
  }
}

export default function AppShell() {
  const { logout } = useAuth();
  const currentYear = new Date().getFullYear();
  const isDebug = bootstrap.mode === "debug";
  const navigate = useNavigate();
  const location = useLocation();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement | null>(null);
  const showPilotRequestsLink = useMemo(() => canViewPilotRequests(), []);
  const viewerProfile = useMemo(() => deriveViewerProfile(), []);

  const isSessionRoute = /^\/sessions\/[^/]+/.test(location.pathname);
  const isPreLabRoute = /^\/labs\/[^/]+\/pre-lab$/.test(location.pathname);
  const isPilotRequestsRoute =
    location.pathname === "/pilot-requests" ||
    location.pathname === "/admin/pilot-requests";
  const showCatalogShell =
    !isDebug &&
    (location.pathname === "/labs" || location.pathname === "/reports");

  const activeCatalogLabel =
    location.pathname === "/labs"
      ? "Catalog"
      : location.pathname === "/reports"
        ? "Reports"
        : null;

  useEffect(() => {
    const handleDocumentClick = (event: MouseEvent) => {
      if (!userMenuRef.current) return;
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (!userMenuRef.current.contains(target)) {
        setIsUserMenuOpen(false);
      }
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsUserMenuOpen(false);
      }
    };

    document.addEventListener("mousedown", handleDocumentClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleDocumentClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, []);

  if (showCatalogShell) {
    return (
      <div className="h-screen overflow-hidden bg-black font-sans text-slate-100 antialiased">
        <div className="relative flex h-full overflow-hidden">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(132,204,22,0.12),transparent_30%),radial-gradient(circle_at_top_right,rgba(34,197,94,0.10),transparent_28%),linear-gradient(180deg,#020617_0%,#020617_40%,#000_100%)]" />

          <div className="pointer-events-none absolute top-0 right-8 hidden h-80 w-96 opacity-20 lg:block">
            <div className="h-full w-full bg-[linear-gradient(180deg,rgba(132,204,22,0.35)_1px,transparent_1px)] bg-[size:18px_18px]" />
          </div>

          <aside className="relative z-20 flex w-64 min-w-64 shrink-0 flex-col border-r border-lime-500/20 bg-black/80">
            <div className="flex h-20 items-center gap-3 border-b border-lime-500/20 px-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-lime-500/15 text-lime-300 ring-1 ring-lime-400/40 shadow-[0_0_22px_rgba(132,204,22,0.25)]">
                <Shield className="h-6 w-6" />
              </div>
              <span className="text-xl font-extrabold tracking-tight text-slate-100">
                Agent Failure
              </span>
            </div>

            <nav className="space-y-1 px-4 py-4">
              {catalogNavItems.map((item) => {
                const Icon = item.icon;
                const isActive = item.label === activeCatalogLabel;

                return (
                  <button
                    key={item.label}
                    type="button"
                    onClick={() => {
                      if (item.to) navigate(item.to);
                    }}
                    className={[
                      "relative flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold transition",
                      isActive
                        ? "border border-lime-400/40 bg-lime-500/10 text-lime-200 shadow-[0_0_18px_rgba(132,204,22,0.18)] before:absolute before:left-0 before:top-1/2 before:h-8 before:w-1 before:-translate-y-1/2 before:rounded-full before:bg-lime-400 before:shadow-[0_0_16px_rgba(132,204,22,0.9)]"
                        : "text-slate-300 hover:bg-lime-500/5 hover:text-lime-200",
                      item.to ? "" : "cursor-default opacity-70",
                    ].join(" ")}
                  >
                    <Icon className="h-5 w-5" />
                    {item.label}
                  </button>
                );
              })}
            </nav>

            <div className="px-4 py-5">
              <div className="mb-5 border-t border-lime-500/20" />

              <p className="mb-3 px-4 text-xs font-bold uppercase tracking-wide text-slate-500">
                Resources
              </p>

              <div className="space-y-1">
                {resourceItems.map((item) => {
                  const Icon = item.icon;

                  return (
                    <button
                      key={item.label}
                      type="button"
                      className="flex w-full items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-300 transition hover:bg-lime-500/5 hover:text-lime-200"
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </aside>

          <main className="relative flex min-w-0 flex-1 flex-col">
            <header className="sticky top-0 z-10 h-20 border-b border-lime-500/20 bg-black/55 px-5 backdrop-blur md:px-8 lg:px-10">
              <div className="flex h-full items-center justify-between">
                <div />

                <div className="ml-auto flex items-center gap-4">
                  <button
                    type="button"
                    className="rounded-full p-2 text-slate-300 transition hover:bg-lime-500/10 hover:text-lime-200"
                    aria-label="Notifications"
                  >
                    <Bell className="h-5 w-5" />
                  </button>

                  <div className="relative pl-1" ref={userMenuRef}>
                    <button
                      type="button"
                      aria-haspopup="menu"
                      aria-expanded={isUserMenuOpen}
                      onClick={() => setIsUserMenuOpen((open) => !open)}
                      className="flex items-center gap-2 rounded-lg px-2 py-1 text-left transition hover:bg-lime-500/10"
                    >
                      <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-800 text-xs font-extrabold text-slate-100 ring-1 ring-lime-500/20">
                        {viewerProfile.initials}
                      </div>
                      <span className="hidden text-sm font-semibold text-slate-300 sm:inline">
                        {viewerProfile.displayName}
                      </span>
                      <span className="hidden rounded-md border border-lime-500/30 bg-lime-500/10 px-2 py-0.5 text-xs font-bold uppercase tracking-wide text-lime-200 md:inline">
                        {viewerProfile.roleLabel}
                      </span>
                    </button>

                    {isUserMenuOpen && (
                      <div
                        role="menu"
                        className="absolute right-0 z-30 mt-2 w-40 rounded-lg border border-lime-500/30 bg-black/95 p-1 shadow-[0_0_20px_rgba(132,204,22,0.18)] backdrop-blur"
                      >
                        {showPilotRequestsLink ? (
                          <button
                            type="button"
                            role="menuitem"
                            onClick={() => {
                              setIsUserMenuOpen(false);
                              navigate("/pilot-requests");
                            }}
                            className="flex w-full items-center rounded-md px-3 py-2 text-sm font-semibold text-slate-200 transition hover:bg-lime-500/10 hover:text-lime-100"
                          >
                            Pilot Requests
                          </button>
                        ) : null}
                        <button
                          type="button"
                          role="menuitem"
                          onClick={() => {
                            setIsUserMenuOpen(false);
                            logout();
                          }}
                          className="flex w-full items-center rounded-md px-3 py-2 text-sm font-semibold text-slate-200 transition hover:bg-lime-500/10 hover:text-lime-100"
                        >
                          Log Out
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </header>

            <div className="flex-1 overflow-y-auto">
              <Outlet context={bootstrap} />
            </div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div
      style={
        isDebug
          ? {
              minHeight: "100vh",
              display: "flex",
              flexDirection: "column",
              background: "#040704",
              color: "#d7ffd7",
              fontFamily:
                '"Share Tech Mono", "Fira Code", "Courier New", monospace',
            }
          : {
              minHeight: "100vh",
              display: "flex",
              flexDirection: "column",
              color: "#d7ffd7",
              background:
                "radial-gradient(1200px 680px at 8% -2%, rgba(60, 200, 100, 0.16), transparent 50%), radial-gradient(900px 540px at 95% -6%, rgba(46, 125, 50, 0.2), transparent 52%), linear-gradient(180deg, #040704 0%, #071007 52%, #081108 100%)",
              fontFamily:
                '"Share Tech Mono", "Fira Code", "Courier New", monospace',
            }
      }
    >
      {!isSessionRoute ? (
        <header
          style={{
            borderBottom: "1px solid #1b5e20",
            background: isDebug
              ? "linear-gradient(180deg, rgba(10, 18, 10, 0.98), rgba(6, 12, 6, 0.95))"
              : "linear-gradient(180deg, rgba(10, 18, 10, 0.95), rgba(6, 12, 6, 0.9))",
            backdropFilter: isDebug ? undefined : "blur(6px)",
            position: "sticky",
            top: 0,
            zIndex: 3,
          }}
        >
          <div
            style={{
              maxWidth: isSessionRoute ? undefined : 1240,
              margin: isSessionRoute ? 0 : "0 auto",
              padding: isSessionRoute ? "14px 16px" : "14px 24px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: 22,
                  fontWeight: 700,
                  letterSpacing: 0.4,
                  color: "#8bff8f",
                  fontFamily:
                    '"Orbitron", "Space Grotesk", "Avenir Next Condensed", sans-serif',
                  textTransform: isDebug ? undefined : "uppercase",
                }}
              >
                Agent Failure
              </div>
              <div
                style={{
                  fontSize: 12,
                  opacity: isDebug ? 0.7 : 1,
                  color: "#7ea683",
                  letterSpacing: isDebug ? undefined : 0.3,
                }}
              >
                {isDebug
                  ? "Demo mode: auth deferred for P1 usability sprint"
                  : "Cyberrange Demo Surface"}
              </div>
            </div>
            {isSessionRoute ? (
              <div />
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                {isPreLabRoute || isPilotRequestsRoute ? (
                  <button
                    type="button"
                    onClick={() => navigate("/labs")}
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      padding: "7px 10px",
                      borderRadius: 8,
                      cursor: "pointer",
                      border: "1px solid #2e7d32",
                      background: "#102810",
                      color: "#b6ffb9",
                    }}
                  >
                    Back to Labs
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={logout}
                  style={{
                    fontSize: 12,
                    fontWeight: 700,
                    padding: "7px 10px",
                    borderRadius: 8,
                    cursor: "pointer",
                    border: "1px solid #7a2f3a",
                    background: "#3a1118",
                    color: "#ffd7de",
                  }}
                >
                  Log Out
                </button>
              </div>
            )}
          </div>
          {bootstrap.mode === "debug" && (
            <nav
              style={{
                maxWidth: isSessionRoute ? undefined : 1120,
                margin: isSessionRoute ? 0 : "0 auto",
                padding: isSessionRoute ? "0 16px 10px" : "0 20px 10px",
                display: "flex",
                gap: 16,
              }}
            >
              <NavLink to="/labs" style={navLinkStyle}>
                Labs
              </NavLink>
              <NavLink to="/admin/pilot-requests" style={navLinkStyle}>
                Pilot Requests
              </NavLink>
            </nav>
          )}
        </header>
      ) : null}
      <main
        style={{
          maxWidth: isSessionRoute ? undefined : 1240,
          margin: isSessionRoute ? 0 : "0 auto",
          padding: isSessionRoute ? 0 : isDebug ? "20px" : "28px 24px 34px",
          flex: "1 1 auto",
          minHeight: 0,
          width: "100%",
          display: isSessionRoute ? "flex" : undefined,
          flexDirection: isSessionRoute ? "column" : undefined,
        }}
      >
        <Outlet context={bootstrap} />
      </main>
      <footer
        style={{
          borderTop: "1px solid #1b5e20",
          padding: isSessionRoute ? "10px 16px" : "10px 24px",
          color: "#7ea683",
          fontSize: 12,
          background: "rgba(6, 12, 6, 0.9)",
        }}
      >
        <div
          style={{
            maxWidth: isSessionRoute ? undefined : 1240,
            margin: isSessionRoute ? 0 : "0 auto",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <span>© {currentYear} Agent Failure</span>
          <nav
            aria-label="Footer links"
            style={{ display: "flex", gap: 12, flexWrap: "wrap" }}
          >
            <a
              href="https://agent-failure.local/docs"
              style={{ color: "inherit", textDecoration: "none" }}
            >
              Docs
            </a>
            <a
              href="https://agent-failure.local/privacy"
              style={{ color: "inherit", textDecoration: "none" }}
            >
              Privacy
            </a>
            <a
              href="https://agent-failure.local/terms"
              style={{ color: "inherit", textDecoration: "none" }}
            >
              Terms
            </a>
            <a
              href="https://agent-failure.local/support"
              style={{ color: "inherit", textDecoration: "none" }}
            >
              Report issue
            </a>
          </nav>
        </div>
      </footer>
    </div>
  );
}
