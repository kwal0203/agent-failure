import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/context";
import type { ShellBootstrap } from "../shell/context";

const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
  textDecoration: "none",
  color: isActive ? "#0a3a7a" : "#2a2f37",
  borderBottom: isActive ? "2px solid #0a3a7a" : "2px solid transparent",
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
  const showBackToApp = ["/labs", "/history", "/trace"].includes(
    location.pathname,
  );
  const headerBackTarget = showBackToApp ? "/app" : "/labs";
  const headerBackLabel = showBackToApp ? "Back to App" : "Back to Labs";

  return (
    <div
      style={
        isDebug
          ? {
              minHeight: "100vh",
              display: "flex",
              flexDirection: "column",
              background: "#f5f7fb",
              color: "#10131a",
            }
          : {
              minHeight: "100vh",
              display: "flex",
              flexDirection: "column",
              color: "#d7f5ff",
              background:
                "radial-gradient(1200px 680px at 8% -2%, rgba(0, 230, 255, 0.18), transparent 50%), radial-gradient(900px 540px at 95% -6%, rgba(28, 160, 255, 0.22), transparent 52%), linear-gradient(180deg, #040b14 0%, #071321 52%, #081726 100%)",
              fontFamily:
                '"Space Grotesk", "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif',
            }
      }
    >
      <header
        style={{
          borderBottom: isDebug ? "1px solid #d9dee8" : "1px solid #1d3850",
          background: isDebug
            ? "#ffffff"
            : "linear-gradient(180deg, rgba(6, 20, 34, 0.9), rgba(6, 20, 34, 0.75))",
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
                color: isDebug ? "#10131a" : "#e8fbff",
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
                color: isDebug ? undefined : "#73b6ce",
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
              <button
                type="button"
                onClick={() => navigate(headerBackTarget)}
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  padding: "7px 10px",
                  borderRadius: 8,
                  cursor: "pointer",
                  border: isDebug ? "1px solid #cfd8e3" : "1px solid #2d5a7d",
                  background: isDebug ? "#ffffff" : "#0b2a43",
                  color: isDebug ? "#0f1724" : "#cff6ff",
                }}
              >
                {headerBackLabel}
              </button>
              <div
                style={{
                  fontSize: 13,
                  opacity: isDebug ? 0.8 : 1,
                  color: isDebug ? undefined : "#9fe4fb",
                  background: isDebug ? undefined : "rgba(8, 31, 50, 0.72)",
                  border: isDebug ? undefined : "1px solid #285272",
                  padding: isDebug ? undefined : "6px 10px",
                  borderRadius: isDebug ? undefined : 8,
                }}
              >
                Learner: <strong>{bootstrap.learnerLabel}</strong>
              </div>
              <button
                type="button"
                onClick={logout}
                style={{
                  fontSize: 12,
                  fontWeight: 700,
                  padding: "7px 10px",
                  borderRadius: 8,
                  cursor: "pointer",
                  border: isDebug ? "1px solid #cfd8e3" : "1px solid #7a2f3a",
                  background: isDebug ? "#ffffff" : "#3a1118",
                  color: isDebug ? "#0f1724" : "#ffd7de",
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
          borderTop: isDebug ? "1px solid #d9dee8" : "1px solid #1d3850",
          padding: isSessionRoute ? "10px 16px" : "10px 24px",
          color: isDebug ? "#516171" : "#83b5c8",
          fontSize: 12,
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
