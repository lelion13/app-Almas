import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { ApiError, apiFetch } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";

type Session = {
  id: string; session_date: string; start_time: string; duration_minutes: number;
  capacity: number; level: string; status: string;
};
type Booking = { id: string; student_id: string; status: string; source: string; created_at: string };

export default function InstructorAgendaPage() {
  const { me } = useAuth();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [selected, setSelected] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function loadSessions() {
    try {
      setSessions(await apiFetch<Session[]>("/api/v1/studio/instructor/sessions"));
    } catch (e) { setError(e instanceof ApiError ? e.message : "No se pudo cargar la agenda."); }
  }

  useEffect(() => { void loadSessions(); }, []);
  if (me?.role !== "instructor") return <Navigate to="/" replace />;

  async function selectSession(session: Session) {
    setSelected(session); setNotice(null); setError(null);
    try {
      setBookings(await apiFetch<Booking[]>(`/api/v1/studio/instructor/sessions/${session.id}/bookings`));
    } catch (e) { setError(e instanceof ApiError ? e.message : "No se pudieron cargar las reservas."); }
  }

  async function setAttendance(bookingId: string, status: "presente" | "ausente" | "tarde") {
    setError(null); setNotice(null);
    try {
      await apiFetch("/api/v1/studio/instructor/attendance", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ booking_id: bookingId, status }),
      });
      setNotice("Asistencia registrada.");
    } catch (e) { setError(e instanceof ApiError ? e.message : "No se pudo registrar la asistencia."); }
  }

  return <div className="space-y-6">
    <div><h1 className="text-2xl font-semibold text-slate-900">Mi agenda</h1><p className="mt-1 text-sm text-slate-600">Elegí una clase para registrar asistencia.</p></div>
    {error && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
    {notice && <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{notice}</p>}
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="rounded-xl border border-slate-200 bg-white">
        <h2 className="border-b border-slate-200 px-4 py-3 font-medium text-slate-900">Próximas clases</h2>
        <ul className="divide-y divide-slate-100">
          {sessions.length === 0 && <li className="px-4 py-6 text-sm text-slate-500">No tenés sesiones programadas.</li>}
          {sessions.map((session) => <li key={session.id}>
            <button type="button" onClick={() => void selectSession(session)} className={`w-full px-4 py-3 text-left text-sm hover:bg-slate-50 ${selected?.id === session.id ? "bg-brand-50" : ""}`}>
              <span className="font-medium text-slate-900">{session.session_date} · {session.start_time}</span>
              <span className="block text-xs text-slate-500">{session.duration_minutes} min · nivel {session.level} · {session.status}</span>
            </button>
          </li>)}
        </ul>
      </section>
      <section className="rounded-xl border border-slate-200 bg-white">
        <h2 className="border-b border-slate-200 px-4 py-3 font-medium text-slate-900">{selected ? `Reservas · ${selected.session_date}` : "Reservas"}</h2>
        {!selected ? <p className="px-4 py-6 text-sm text-slate-500">Seleccioná una clase.</p> : <ul className="divide-y divide-slate-100">
          {bookings.length === 0 && <li className="px-4 py-6 text-sm text-slate-500">Esta clase no tiene reservas.</li>}
          {bookings.map((booking) => <li key={booking.id} className="px-4 py-3 text-sm">
            <div className="font-mono text-xs text-slate-600">Alumno {booking.student_id}</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {(["presente", "ausente", "tarde"] as const).map((status) => <button key={status} type="button" onClick={() => void setAttendance(booking.id, status)} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50">{status}</button>)}
            </div>
          </li>)}
        </ul>}
      </section>
    </div>
  </div>;
}
