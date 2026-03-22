import { Navigate, Route, Routes } from "react-router-dom";
import AppShell from "./layout/AppShell";
import HistoryPage from "./pages/HistoryPage";
import LabsPage from "./pages/LabsPage";
import SessionPage from "./pages/SessionPage";
import TracePage from "./pages/TracePage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/labs" replace />} />
        <Route path="/labs" element={<LabsPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/trace" element={<TracePage />} />
        <Route path="/sessions/:sessionId" element={<SessionPage />} />
        <Route path="*" element={<Navigate to="/labs" replace />} />
      </Route>
    </Routes>
  );
}
