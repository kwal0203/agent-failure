import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/context";
import { ProtectedRoute, PublicOnlyRoute } from "./auth/guards";
import AppShell from "./layout/AppShell";
import AppHomePage from "./pages/app/AppHomePage";
import HistoryPage from "./pages/HistoryPage";
import LabsPage from "./pages/LabsPage";
import HomePage from "./pages/public/HomePage";
import LoginPage from "./pages/public/LoginPage";
import SignupPage from "./pages/public/SignupPage";
import SessionPage from "./pages/SessionPage";
import TracePage from "./pages/TracePage";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<HomePage />} />

        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
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

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
