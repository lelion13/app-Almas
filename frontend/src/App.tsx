import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./hooks/useAuth";
import AppShell from "./components/AppShell";
import LoginPage from "./pages/LoginPage";
import ClosingsListPage from "./pages/ClosingsListPage";
import ClosingDetailPage from "./pages/ClosingDetailPage";
import TeachersPage from "./pages/TeachersPage";
import ConciliacionPage from "./pages/ConciliacionPage";
import StudioAdminPage from "./pages/StudioAdminPage";
import InstructorAgendaPage from "./pages/InstructorAgendaPage";
import AlumnoPortalPage from "./pages/AlumnoPortalPage";
import SettingsBackupPage from "./pages/SettingsBackupPage";

function Protected({ children }: { children: ReactNode }) {
  const { token, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-dvh items-center justify-center text-slate-600">
        Cargando…
      </div>
    );
  }
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RoleIndex() {
  const { me } = useAuth();
  if (me?.role === "alumno") return <AlumnoPortalPage />;
  if (me?.role === "instructor") return <InstructorAgendaPage />;
  return <ClosingsListPage />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <Protected>
            <AppShell />
          </Protected>
        }
      >
        <Route index element={<RoleIndex />} />
        <Route path="closings/:id" element={<ClosingDetailPage />} />
        <Route path="teachers" element={<TeachersPage />} />
        <Route path="conciliacion" element={<ConciliacionPage />} />
        <Route path="studio" element={<StudioAdminPage />} />
        <Route path="configuracion" element={<SettingsBackupPage />} />
        <Route path="instructor" element={<InstructorAgendaPage />} />
        <Route path="mis-clases" element={<AlumnoPortalPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
