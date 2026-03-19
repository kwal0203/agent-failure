import { Navigate, Route, Routes } from "react-router-dom";
import SessionPage from "./pages/SessionPage.tsx";

export default function App() {
  return (
    <Routes>
      <Route path="/sessions/:sessionId" element={<SessionPage />} />
      <Route path="*" element={<Navigate to="/sessions/demo-session-id" replace />} />
    </Routes>
  );
}
