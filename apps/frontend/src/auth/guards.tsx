import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./context";
import {
  getEnrollmentRedeemError,
  isEnrollmentApiEnabled,
  PENDING_ENROLLMENT_TOKEN_KEY,
} from "./enrollment";
import { POST_LOGIN_REDIRECT_KEY, resolveSafeNext } from "./redirect";

export function ProtectedRoute() {
  const { isAuthenticated, isBootstrapping } = useAuth();
  const location = useLocation();

  if (isBootstrapping) return null;

  if (!isAuthenticated) {
    const next = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />;
  }

  if (isEnrollmentApiEnabled()) {
    const pendingToken = window.sessionStorage.getItem(
      PENDING_ENROLLMENT_TOKEN_KEY,
    );
    const redeemError = getEnrollmentRedeemError();
    const needsEnrollment = Boolean(pendingToken || redeemError);
    const isEnrollmentRoute = location.pathname === "/enrollment";
    if (needsEnrollment && !isEnrollmentRoute) {
      return <Navigate to="/enrollment" replace />;
    }
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
