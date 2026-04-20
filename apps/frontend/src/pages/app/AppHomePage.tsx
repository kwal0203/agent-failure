import { Link } from "react-router-dom";
import { useAuth } from "../../auth/context";

export default function AppHomePage() {
  const { user, logout } = useAuth();

  return (
    <section>
      <h1 style={{ margin: "0 0 10px" }}>Platform Home</h1>
      <p style={{ margin: "0 0 12px" }}>
        Signed in as <strong>{user?.email ?? "unknown"}</strong>.
      </p>
      <p style={{ margin: "0 0 18px", opacity: 0.85 }}>
        This is the authenticated app entrypoint. Labs, sessions, history, and
        trace are now protected routes.
      </p>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <Link to="/labs">Browse Labs</Link>
        <Link to="/history">History</Link>
        <Link to="/trace">Trace</Link>
        <button type="button" onClick={logout}>
          Log out
        </button>
      </div>
    </section>
  );
}
