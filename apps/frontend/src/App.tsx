import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/context";
import { ProtectedRoute, PublicOnlyRoute } from "./auth/guards";
import AppShell from "./layout/AppShell";
import PilotRequestsAdminPage from "./pages/admin/PilotRequestsAdminPage";
import AppHomePage from "./pages/app/AppHomePage";
import EnrollmentPage from "./pages/EnrollmentPage";
import HistoryPage from "./pages/HistoryPage";
import LabsPage from "./pages/LabsPage";
import PreLabPage from "./pages/PreLabPage";
import ForgotPasswordPage from "./pages/public/ForgotPasswordPage";
import LoginPage from "./pages/public/LoginPage";
import PilotRequestPage from "./pages/public/PilotRequestPage";
import SignupPage from "./pages/public/SignupPage";
import ReportsPage from "./pages/ReportsPage";
import SessionPage from "./pages/SessionPage";
import SessionReportPage from "./pages/SessionReportPage";
import TracePage from "./pages/TracePage";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />

        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/pilot-request" element={<PilotRequestPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/app" element={<AppHomePage />} />
            <Route path="/enrollment" element={<EnrollmentPage />} />
            <Route path="/labs" element={<LabsPage />} />
            <Route path="/labs/:labId/pre-lab" element={<PreLabPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/trace" element={<TracePage />} />
            <Route
              path="/admin/pilot-requests"
              element={<PilotRequestsAdminPage />}
            />
            <Route
              path="/pilot-requests"
              element={<PilotRequestsAdminPage />}
            />
            <Route path="/sessions/:sessionId" element={<SessionPage />} />
            <Route
              path="/sessions/:sessionId/report"
              element={<SessionReportPage />}
            />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </AuthProvider>
  );
}
