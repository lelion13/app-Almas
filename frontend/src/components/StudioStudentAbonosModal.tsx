import { useEffect, useMemo, useState } from "react";
import { ApiError, apiFetch } from "@/services/api";

type Item = Record<string, unknown> & { id: string };

const WEEKDAYS = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const inputClass = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm";
const buttonClass = "rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800 disabled:opacity-60";

function asText(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

type Eligible = {
  booking_id: string;
  series_id: string;
  session_date: string;
  start_time: string;
  activity_id: string;
  covered: boolean;
};

type Props = {
  student: Item;
  onClose: () => void;
};

export default function StudioStudentAbonosModal({ student, onClose }: Props) {
  const [abonos, setAbonos] = useState<Item[]>([]);
  const [aranceles, setAranceles] = useState<Item[]>([]);
  const [series, setSeries] = useState<Item[]>([]);
  const [activities, setActivities] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selectedAbonoId, setSelectedAbonoId] = useState<string | null>(null);
  const [eligible, setEligible] = useState<Eligible[]>([]);
  const [selectedBookings, setSelectedBookings] = useState<string[]>([]);
  const [selectedSeries, setSelectedSeries] = useState<string[]>([]);
  const [arancelId, setArancelId] = useState("");
  const [paidOn, setPaidOn] = useState(() => new Date().toISOString().slice(0, 10));
  const [payAmount, setPayAmount] = useState("");
  const [extraPay, setExtraPay] = useState("");

  const selectedArancel = aranceles.find((a) => a.id === arancelId);
  const maxSeries = Number(selectedArancel?.classes_per_week ?? 0);
  const arancelActivityIds = useMemo(
    () => (Array.isArray(selectedArancel?.activity_ids) ? (selectedArancel!.activity_ids as string[]) : []),
    [selectedArancel],
  );
  const filteredSeries = series.filter((s) => arancelActivityIds.includes(String(s.activity_id)));

  async function reload() {
    const [abonoRows, arancelRows, seriesRows, activityRows] = await Promise.all([
      apiFetch<Item[]>(`/api/v1/studio/abonos?student_id=${student.id}`),
      apiFetch<Item[]>("/api/v1/studio/aranceles"),
      apiFetch<Item[]>("/api/v1/studio/series-options"),
      apiFetch<Item[]>("/api/v1/studio/activities"),
    ]);
    setAbonos(abonoRows);
    setAranceles(arancelRows.filter((a) => a.active !== false));
    setSeries(seriesRows);
    setActivities(activityRows);
  }

  useEffect(() => {
    void reload().catch((e) => setError(e instanceof ApiError ? e.message : "No se pudo cargar."));
  }, [student.id]);

  async function openAbono(abono: Item) {
    setSelectedAbonoId(abono.id);
    setSelectedSeries(Array.isArray(abono.series_ids) ? (abono.series_ids as string[]) : []);
    setExtraPay("");
    const rows = await apiFetch<Eligible[]>(`/api/v1/studio/abonos/${abono.id}/eligible-bookings`);
    setEligible(rows);
    setSelectedBookings(rows.filter((r) => r.covered).map((r) => r.booking_id));
  }

  function toggleSeries(id: string) {
    setSelectedSeries((current) => {
      if (current.includes(id)) return current.filter((x) => x !== id);
      if (maxSeries && current.length >= maxSeries) return current;
      return [...current, id];
    });
  }

  async function createAbono() {
    if (!arancelId) return;
    setBusy(true); setError(null);
    try {
      const body: Record<string, unknown> = {
        student_id: student.id,
        arancel_id: arancelId,
        paid_on: paidOn,
        series_ids: selectedSeries,
        booking_ids: [],
      };
      if (payAmount) {
        body.initial_payment = { amount: Number(payAmount), paid_on: paidOn, method: "efectivo" };
      }
      const created = await apiFetch<Item>("/api/v1/studio/abonos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setArancelId("");
      setPayAmount("");
      setSelectedSeries([]);
      await reload();
      await openAbono(created);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo crear el abono.");
    } finally {
      setBusy(false);
    }
  }

  async function saveLinks() {
    if (!selectedAbonoId) return;
    setBusy(true); setError(null);
    try {
      await apiFetch(`/api/v1/studio/abonos/${selectedAbonoId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ series_ids: selectedSeries, booking_ids: selectedBookings }),
      });
      await reload();
      const abono = (await apiFetch<Item[]>(`/api/v1/studio/abonos?student_id=${student.id}`)).find((a) => a.id === selectedAbonoId);
      if (abono) await openAbono(abono);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo guardar.");
    } finally {
      setBusy(false);
    }
  }

  async function addPayment() {
    if (!selectedAbonoId || !extraPay) return;
    setBusy(true); setError(null);
    try {
      await apiFetch(`/api/v1/studio/abonos/${selectedAbonoId}/payments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount: Number(extraPay), method: "efectivo" }),
      });
      setExtraPay("");
      await reload();
      const abono = abonos.find((a) => a.id === selectedAbonoId) ?? (await apiFetch<Item[]>(`/api/v1/studio/abonos?student_id=${student.id}`)).find((a) => a.id === selectedAbonoId);
      if (abono) await openAbono(abono);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo registrar el pago.");
    } finally {
      setBusy(false);
    }
  }

  async function annul(abonoId: string) {
    if (!window.confirm("¿Anular este abono? Los turnos asociados quedarán sin cobertura.")) return;
    setBusy(true); setError(null);
    try {
      await apiFetch(`/api/v1/studio/abonos/${abonoId}/annul`, { method: "POST" });
      setSelectedAbonoId(null);
      await reload();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo anular.");
    } finally {
      setBusy(false);
    }
  }

  const activityName = (id: string) => asText(activities.find((a) => a.id === id)?.name ?? id);
  const seriesLabel = (s: Item) =>
    `${activityName(String(s.activity_id))} · ${WEEKDAYS[Number(s.weekday) || 0]} ${String(s.start_time).slice(0, 5)}`;

  const selected = abonos.find((a) => a.id === selectedAbonoId);
  const selectedAbonoArancel = aranceles.find((a) => a.id === selected?.arancel_id);
  const selectedAbonoActivityIds = Array.isArray(selectedAbonoArancel?.activity_ids)
    ? (selectedAbonoArancel!.activity_ids as string[])
    : [];
  const seriesForSelectedAbono = series.filter((s) => selectedAbonoActivityIds.includes(String(s.activity_id)));

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center" role="dialog" aria-modal="true">
      <div className="flex max-h-[92dvh] w-full max-w-2xl flex-col overflow-hidden rounded-xl bg-white shadow-lg">
        <div className="border-b border-slate-100 p-4">
          <h3 className="text-lg font-semibold text-slate-900">Abonos · {asText(student.full_name)}</h3>
          <p className="mt-1 text-xs text-slate-500">Al guardar series se generan los turnos del periodo en el calendario. Los días usan la misma convención que el calendario (Dom=0).</p>
          {error && <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
        </div>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="mb-2 text-sm font-medium text-slate-800">Nuevo abono</div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1 text-sm sm:col-span-2">
                <span>Arancel</span>
                <select className={inputClass} value={arancelId} onChange={(e) => { setArancelId(e.target.value); setSelectedSeries([]); }}>
                  <option value="">Elegí…</option>
                  {aranceles.map((a) => <option key={a.id} value={a.id}>{asText(a.name)} · ${asText(a.price)} · {asText(a.classes_per_week)}/sem</option>)}
                </select>
              </label>
              <label className="space-y-1 text-sm"><span>Fecha de pago</span><input className={inputClass} type="date" value={paidOn} onChange={(e) => setPaidOn(e.target.value)} /></label>
              <label className="space-y-1 text-sm"><span>Pago inicial (opcional)</span><input className={inputClass} type="number" min="0" step="0.01" value={payAmount} onChange={(e) => setPayAmount(e.target.value)} /></label>
            </div>
            {arancelId && (
              <div className="mt-3 space-y-2">
                <div className="text-xs text-slate-600">Series (hasta {maxSeries})</div>
                <div className="flex flex-col gap-1">
                  {filteredSeries.map((s) => (
                    <label key={s.id} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" checked={selectedSeries.includes(s.id)} onChange={() => toggleSeries(s.id)} disabled={!selectedSeries.includes(s.id) && selectedSeries.length >= maxSeries} />
                      {seriesLabel(s)}
                    </label>
                  ))}
                  {!filteredSeries.length && <p className="text-xs text-slate-500">No hay series activas para las actividades del arancel. Asigná instructores en el calendario.</p>}
                </div>
              </div>
            )}
            <button type="button" className={`${buttonClass} mt-3`} disabled={busy || !arancelId} onClick={() => void createAbono()}>{busy ? "Guardando…" : "Crear abono"}</button>
          </div>

          <div>
            <div className="mb-2 text-sm font-medium text-slate-800">Abonos del alumno</div>
            {!abonos.length ? (
              <p className="text-sm text-slate-500">Sin abonos todavía.</p>
            ) : (
              <ul className="divide-y rounded-lg border border-slate-200">
                {abonos.map((a) => (
                  <li key={a.id} className="flex flex-col gap-2 px-3 py-2 text-sm sm:flex-row sm:items-center sm:justify-between">
                    <button type="button" className="text-left" onClick={() => void openAbono(a)}>
                      <div className="font-medium">{asText(a.arancel_name)} · {asText(a.status)}</div>
                      <div className="text-xs text-slate-500">{asText(a.starts_on)} → {asText(a.ends_on)} · pagado {asText(a.amount_paid)} / {asText(a.agreed_amount)} (debe {asText(a.amount_due)})</div>
                    </button>
                    {a.status === "active" && (
                      <button type="button" className="rounded-lg border border-red-200 px-2 py-1 text-xs text-red-700" onClick={() => void annul(a.id)}>Anular</button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>

          {selected && selected.status === "active" && (
            <div className="rounded-lg border border-teal-200 bg-teal-50/40 p-3">
              <div className="text-sm font-medium text-slate-900">Editar · {asText(selected.arancel_name)}</div>
              <div className="mt-2 space-y-1">
                <div className="text-xs font-medium text-slate-600">Series</div>
                {seriesForSelectedAbono.map((s) => {
                  const max = Number(aranceles.find((x) => x.id === selected.arancel_id)?.classes_per_week ?? 99);
                  return (
                    <label key={s.id} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={selectedSeries.includes(s.id)}
                        disabled={!selectedSeries.includes(s.id) && selectedSeries.length >= max}
                        onChange={() => {
                          setSelectedSeries((current) => {
                            if (current.includes(s.id)) return current.filter((x) => x !== s.id);
                            if (current.length >= max) return current;
                            return [...current, s.id];
                          });
                        }}
                      />
                      {seriesLabel(s)}
                    </label>
                  );
                })}
              </div>
              <div className="mt-3 space-y-1">
                <div className="text-xs font-medium text-slate-600">Turnos elegibles del periodo</div>
                {!eligible.length ? (
                  <p className="text-xs text-slate-500">No hay turnos elegibles (o aún no hay series).</p>
                ) : eligible.map((row) => (
                  <label key={row.booking_id} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={selectedBookings.includes(row.booking_id)}
                      onChange={() => setSelectedBookings((cur) => cur.includes(row.booking_id) ? cur.filter((x) => x !== row.booking_id) : [...cur, row.booking_id])}
                    />
                    {row.session_date} {String(row.start_time).slice(0, 5)} · {activityName(row.activity_id)}
                  </label>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" className={buttonClass} disabled={busy} onClick={() => void saveLinks()}>Guardar series y turnos</button>
                <input className={`${inputClass} max-w-[140px]`} type="number" min="0" step="0.01" placeholder="Saldar $" value={extraPay} onChange={(e) => setExtraPay(e.target.value)} />
                <button type="button" className="rounded-lg border px-3 py-2 text-sm" disabled={busy || !extraPay} onClick={() => void addPayment()}>Registrar pago</button>
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end border-t border-slate-100 p-4">
          <button type="button" className="rounded-lg border px-3 py-2 text-sm" onClick={onClose}>Cerrar</button>
        </div>
      </div>
    </div>
  );
}
