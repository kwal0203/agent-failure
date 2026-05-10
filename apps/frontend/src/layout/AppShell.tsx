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

export default function AppShell() {
  const { logout } = useAuth();
  const currentYear = new Date().getFullYear();
  const isDebug = bootstrap.mode === "debug";
  const navigate = useNavigate();
  const location = useLocation();
  const isSessionRoute = /^\/sessions\/[^/]+/.test(location.pathname);
  const isPreLabRoute = /^\/labs\/[^/]+\/pre-lab$/.test(location.pathname);
  const isLabsCatalogRoute = location.pathname === "/labs";
  const hideShellChrome = !isDebug && (isLabsCatalogRoute || isPreLabRoute);

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
      {!hideShellChrome && (
        <header
          style={{
            borderBottom: isDebug ? "1px solid #1b5e20" : "1px solid #1b5e20",
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
                  color: isDebug ? "#8bff8f" : "#8bff8f",
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
                  color: isDebug ? "#7ea683" : "#7ea683",
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
                {isPreLabRoute ? (
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
                    border: isDebug ? "1px solid #7a2f3a" : "1px solid #7a2f3a",
                    background: isDebug ? "#3a1118" : "#3a1118",
                    color: isDebug ? "#ffd7de" : "#ffd7de",
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
              <NavLink to="/history" style={navLinkStyle}>
                History
              </NavLink>
              <NavLink to="/trace" style={navLinkStyle}>
                Trace
              </NavLink>
            </nav>
          )}
        </header>
      )}
      <main
        style={{
          maxWidth: hideShellChrome
            ? undefined
            : isSessionRoute
              ? undefined
              : 1240,
          margin: hideShellChrome ? 0 : isSessionRoute ? 0 : "0 auto",
          padding: hideShellChrome
            ? 0
            : isSessionRoute
              ? 0
              : isDebug
                ? "20px"
                : "28px 24px 34px",
          flex: "1 1 auto",
          minHeight: 0,
          width: "100%",
          display: isSessionRoute ? "flex" : undefined,
          flexDirection: isSessionRoute ? "column" : undefined,
        }}
      >
        <Outlet context={bootstrap} />
      </main>
      {!hideShellChrome && (
        <footer
          style={{
            borderTop: isDebug ? "1px solid #1b5e20" : "1px solid #1b5e20",
            padding: isSessionRoute ? "10px 16px" : "10px 24px",
            color: isDebug ? "#7ea683" : "#7ea683",
            fontSize: 12,
            background: isDebug ? "rgba(6, 12, 6, 0.9)" : "rgba(6, 12, 6, 0.9)",
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
      )}
    </div>
  );
}
