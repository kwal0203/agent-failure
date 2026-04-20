import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./context";
import { POST_LOGIN_REDIRECT_KEY, resolveSafeNext } from "./redirect";

export function ProtectedRoute() {
  const { isAuthenticated, isBootstrapping } = useAuth();
  const location = useLocation();

  if (isBootstrapping) return null;

  if (!isAuthenticated) {
    const next = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />;
  }

  return <Outlet />;
}

export function PublicOnlyRoute() {
  const { isAuthenticated, isBootstrapping } = useAuth();
  const location = useLocation();

  if (isBootstrapping) return null;

  if (isAuthenticated) {
    const pendingNext = window.sessionStorage.getItem(POST_LOGIN_REDIRECT_KEY);
    if (pendingNext) {
      window.sessionStorage.removeItem(POST_LOGIN_REDIRECT_KEY);
      return <Navigate to={resolveSafeNext(pendingNext)} replace />;
    }

    const search = new URLSearchParams(location.search);
    const next = resolveSafeNext(search.get("next"));
    return <Navigate to={next} replace />;
  }

  return <Outlet />;
}
