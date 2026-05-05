import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/context";
import { ProtectedRoute, PublicOnlyRoute } from "./auth/guards";
import AppShell from "./layout/AppShell";
import AppHomePage from "./pages/app/AppHomePage";
import HistoryPage from "./pages/HistoryPage";
import LabsPage from "./pages/LabsPage";
import ForgotPasswordPage from "./pages/public/ForgotPasswordPage";
import LoginPage from "./pages/public/LoginPage";
import SignupPage from "./pages/public/SignupPage";
import SessionPage from "./pages/SessionPage";
import TracePage from "./pages/TracePage";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />

        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/app" element={<AppHomePage />} />
            <Route path="/labs" element={<LabsPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/trace" element={<TracePage />} />
            <Route path="/sessions/:sessionId" element={<SessionPage />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </AuthProvider>
  );
}
