import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./context";
import {
  getEnrollmentRedeemError,
  isEnrollmentApiEnabled,
  PENDING_ENROLLMENT_TOKEN_KEY,
} from "./enrollment";
import { POST_LOGIN_REDIRECT_KEY, resolveSafeNext } from "./redirect";

function AuthTransitionScreen() {
  return (
    <div className="min-h-screen bg-black text-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl items-center justify-center px-6">
        <div className="rounded-xl border border-lime-400/30 bg-black/50 px-5 py-3 text-sm text-lime-200 shadow-[0_0_24px_rgba(132,204,22,0.2)]">
          Loading session...
        </div>
      </div>
    </div>
  );
}

export function ProtectedRoute() {
  const { isAuthenticated, isBootstrapping, isAuthTransitioning } = useAuth();
  const location = useLocation();

  if (isBootstrapping || isAuthTransitioning) return <AuthTransitionScreen />;

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
  const { isAuthenticated, isBootstrapping, isAuthTransitioning } = useAuth();
  const location = useLocation();

  if (isBootstrapping || isAuthTransitioning) return <AuthTransitionScreen />;

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
