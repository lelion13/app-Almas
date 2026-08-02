import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { ApiError, apiFetch } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";

type Pack = { id: string; remaining_credits: number; starts_on: string; expires_on: string; scope: string; payment_status: string };
type Booking = { id: string; session_id: string; pack_id: string; status: string; created_at: string };
type Session = { id: string; session_date: string; start_time: string; duration_minutes: number; capacity: number; level: string; status: string };
type Waitlist = { id: string; session_id: string; position: number };

export default function AlumnoPortalPage() {
  const { me } = useAuth();
  const [packs, setPacks] = useState<Pack[]>([]);
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [waitlists, setWaitlists] = useState<Waitlist[]>([]);
  const [selectedPack, setSelectedPack] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    try {
      const [nextPacks, nextBookings, nextSessions, nextWaitlists] = await Promise.all([
        apiFetch<Pack[]>("/api/v1/studio/me/packs"),
        apiFetch<Booking[]>("/api/v1/studio/me/bookings"),
        apiFetch<Session[]>("/api/v1/studio/me/sessions"),
        apiFetch<Waitlist[]>("/api/v1/studio/me/waitlist"),
      ]);
      setPacks(nextPacks); setBookings(nextBookings); setSessions(nextSessions); setWaitlists(nextWaitlists);
      if (!selectedPack && nextPacks.length) setSelectedPack(nextPacks[0].id);
    } catch (e) { setError(e instanceof ApiError ? e.message : "No se pudieron cargar tus clases."); }
  }

  useEffect(() => { void load(); }, []);
  if (me?.role !== "alumno") return <Navigate to="/" replace />;

  async function request(path: string, body?: unknown, success = "Acción realizada.") {
    setError(null); setNotice(null);
    try {
      const result = await apiFetch<Waitlist | unknown>(path, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      if (path === "/api/v1/studio/me/waitlist") setWaitlists((current) => [...current, result as Waitlist]);
      setNotice(success);
      await load();
    } catch (e) { setError(e instanceof ApiError ? e.message : "No se pudo completar la acción."); }
  }

  const activePacks = packs.filter((pack) => pack.remaining_credits > 0);
  const waitlistFor = (sessionId: string) => waitlists.find((entry) => entry.session_id === sessionId);

  return <div className="space-y-6">
    <div><h1 className="text-2xl font-semibold text-slate-900">Mis clases</h1><p className="mt-1 text-sm text-slate-600">Reservá, cancelá y administrá tus clases.</p></div>
    {error && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
    {notice && <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{notice}</p>}

    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-slate-900">Mis paquetes</h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {packs.length === 0 && <p className="text-sm text-slate-500">No tenés paquetes asignados.</p>}
        {packs.map((pack) => <article key={pack.id} className="rounded-xl border border-slate-200 bg-white p-4 text-sm">
          <p className="font-medium text-slate-900">{pack.remaining_credits} clases disponibles</p>
          <p className="mt-1 text-xs text-slate-500">Vence {pack.expires_on} · {pack.scope.replace("_", " ")}</p>
        </article>)}
      </div>
    </section>

    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-lg font-semibold text-slate-900">Clases disponibles</h2>
        <select className="rounded-lg border border-slate-300 px-3 py-2 text-sm" value={selectedPack} onChange={(e) => setSelectedPack(e.target.value)}>
          <option value="">Elegí un paquete</option>{activePacks.map((pack) => <option key={pack.id} value={pack.id}>{pack.remaining_credits} créditos · vence {pack.expires_on}</option>)}
        </select>
      </div>
      <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
        {sessions.length === 0 && <li className="px-4 py-6 text-sm text-slate-500">No hay clases disponibles.</li>}
        {sessions.map((session) => {
          const waitlist = waitlistFor(session.id);
          return <li key={session.id} className="flex flex-col gap-2 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
            <div><p className="font-medium text-slate-900">{session.session_date} · {session.start_time}</p><p className="text-xs text-slate-500">{session.duration_minutes} min · nivel {session.level}</p></div>
            <div className="flex gap-2">
              <button type="button" disabled={!selectedPack} onClick={() => void request("/api/v1/studio/me/book", { session_id: session.id, pack_id: selectedPack }, "Clase reservada.")} className="rounded-lg bg-brand-700 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">Reservar</button>
              {!waitlist ? <button type="button" onClick={() => void request("/api/v1/studio/me/waitlist", { session_id: session.id }, "Te sumaste a la lista de espera.")} className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs">Lista de espera</button> : <button type="button" disabled={!selectedPack} onClick={() => void request(`/api/v1/studio/me/waitlist/${waitlist.id}/confirm`, { pack_id: selectedPack }, "Reserva confirmada.")} className="rounded-lg border border-brand-300 px-3 py-1.5 text-xs text-brand-800 disabled:opacity-50">Confirmar espera</button>}
            </div>
          </li>;
        })}
      </ul>
    </section>

    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-slate-900">Mis reservas</h2>
      <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
        {bookings.length === 0 && <li className="px-4 py-6 text-sm text-slate-500">Todavía no tenés reservas.</li>}
        {bookings.map((booking) => <li key={booking.id} className="flex items-center justify-between gap-3 px-4 py-3 text-sm">
          <div><p className="font-medium text-slate-900">Reserva {booking.status}</p><p className="font-mono text-xs text-slate-500">Sesión {booking.session_id}</p></div>
          {booking.status !== "cancelled" && <button type="button" onClick={() => void request(`/api/v1/studio/me/bookings/${booking.id}/cancel`, undefined, "Reserva cancelada.")} className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-700">Cancelar</button>}
        </li>)}
      </ul>
    </section>
  </div>;
}
