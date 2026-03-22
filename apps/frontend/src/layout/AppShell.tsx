import { NavLink, Outlet } from "react-router-dom";
import type { ShellBootstrap } from "../shell/context";

const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
  textDecoration: "none",
  color: isActive ? "#0a3a7a" : "#2a2f37",
  borderBottom: isActive ? "2px solid #0a3a7a" : "2px solid transparent",
  padding: "8px 4px",
  fontWeight: isActive ? 700 : 500,
});

const bootstrap: ShellBootstrap = {
  mode: "demo",
  learnerLabel: "Demo Learner",
  apiBaseUrl: "http://localhost:8000",
};

export default function AppShell() {
  return (
    <div style={{ minHeight: "100vh", background: "#f5f7fb", color: "#10131a" }}>
      <header
        style={{
          borderBottom: "1px solid #d9dee8",
          background: "#ffffff",
          position: "sticky",
          top: 0,
          zIndex: 1,
        }}
      >
        <div
          style={{
            maxWidth: 1120,
            margin: "0 auto",
            padding: "12px 20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontSize: 18, fontWeight: 700 }}>Agent Failure Lab</div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>
              Demo mode: auth deferred for P1 usability sprint
            </div>
          </div>
          <div style={{ fontSize: 13, opacity: 0.8 }}>
            Learner: <strong>{bootstrap.learnerLabel}</strong>
          </div>
        </div>
        <nav style={{ maxWidth: 1120, margin: "0 auto", padding: "0 20px 10px", display: "flex", gap: 16 }}>
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
      </header>
      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "20px" }}>
        <Outlet context={bootstrap} />
      </main>
    </div>
  );
}
