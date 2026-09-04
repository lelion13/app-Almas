import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

export default function InstructorAgendaPage() {
  const { me } = useAuth();
  if (me?.role !== "instructor") return <Navigate to="/" replace />;

  return (
    <div className="mx-auto max-w-lg space-y-4 py-8">
      <h1 className="text-2xl font-semibold text-slate-900">Mi agenda</h1>
      <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
        La agenda de clases y la asistencia están en reconstrucción. Pronto vas a poder gestionar tus sesiones acá.
      </p>
    </div>
  );
}
