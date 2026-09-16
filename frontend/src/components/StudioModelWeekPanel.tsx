import { useEffect, useMemo, useState } from "react";
import { ApiError, apiFetch } from "@/services/api";

type Item = Record<string, unknown> & { id: string };

type ModelStudent = { student_id: string; student_name: string };
type ModelCell = {
  weekday: number;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  capacity: number;
  booked_count: number;
  remaining_capacity: number;
  slot_id?: string | null;
  instructor_id?: string | null;
  instructor_name?: string | null;
  students: ModelStudent[];
};
type ModelWeek = {
  room_id: string;
  room_name: string;
  site_name: string;
  activity_id: string;
  activity_name: string;
  capacity: number;
  cells: ModelCell[];
};

const WEEKDAY_SHORT = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];
const WEEKDAY_LABELS = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
const inputClass = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm";
const buttonClass = "rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800 disabled:opacity-60";

function toHm(value: string) {
  return String(value).slice(0, 5);
}

function asText(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

type Props = {
  sites: Item[];
  rooms: Item[];
  activities: Item[];
  instructors: Item[];
  students: Item[];
};

export default function StudioModelWeekPanel({ sites, rooms, activities, instructors, students }: Props) {
  const [siteId, setSiteId] = useState("");
  const [roomId, setRoomId] = useState("");
  const [activityId, setActivityId] = useState("");
  const [data, setData] = useState<ModelWeek | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<ModelCell | null>(null);
  const [instructorId, setInstructorId] = useState("");
  const [studentIds, setStudentIds] = useState<string[]>([]);
  const [modalError, setModalError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  const activeSites = sites.filter((s) => s.active !== false);
  const activeActivities = activities.filter((a) => a.active !== false);
  const filteredRooms = rooms.filter((room) => {
    if (room.active === false) return false;
    if (siteId && String(room.site_id) !== siteId) return false;
    if (activityId) {
      const activity = activities.find((item) => item.id === activityId);
      const ids = Array.isArray(activity?.room_ids) ? (activity.room_ids as string[]) : [];
      if (!ids.includes(room.id)) return false;
    }
    return true;
  });
  const activeStudents = students.filter((s) => s.active !== false);
  const instructorsForActivity = useMemo(
    () =>
      instructors.filter((instructor) => {
        if (instructor.active === false) return false;
        if (!activityId) return false;
        const ids = Array.isArray(instructor.activity_ids) ? (instructor.activity_ids as string[]) : [];
        return ids.includes(activityId);
      }),
    [instructors, activityId],
  );

  useEffect(() => {
    if (!roomId) return;
    const stillValid = filteredRooms.some((r) => r.id === roomId);
    if (!stillValid) setRoomId("");
  }, [roomId, filteredRooms]);

  useEffect(() => {
    if (!roomId || !activityId) {
      setData(null);
      return;
    }
    let cancelled = false;
    async function load() {
      setBusy(true);
      setError(null);
      try {
        const params = new URLSearchParams({ room_id: roomId, activity_id: activityId });
        const week = await apiFetch<ModelWeek>(`/api/v1/studio/model-week?${params}`);
        if (!cancelled) setData(week);
      } catch (e) {
        if (!cancelled) {
          setData(null);
          setError(e instanceof ApiError ? e.message : "No se pudo cargar la semana modelo.");
        }
      } finally {
        if (!cancelled) setBusy(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [roomId, activityId, reloadToken]);

  function openCell(cell: ModelCell) {
    setSelected(cell);
    setInstructorId(cell.instructor_id ? String(cell.instructor_id) : "");
    setStudentIds(cell.students.map((s) => s.student_id));
    setModalError(null);
  }

  function toggleStudent(id: string) {
    setStudentIds((current) => {
      if (current.includes(id)) return current.filter((x) => x !== id);
      const cap = data?.capacity ?? selected?.capacity ?? 0;
      if (cap && current.length >= cap) return current;
      return [...current, id];
    });
  }

  async function saveCell() {
    if (!selected || !roomId || !activityId) return;
    if (studentIds.length && !instructorId) {
      setModalError("Seleccioná un instructor.");
      return;
    }
    setSaving(true);
    setModalError(null);
    try {
      const body: Record<string, unknown> = {
        room_id: roomId,
        activity_id: activityId,
        weekday: selected.weekday,
        start_time: selected.start_time,
        student_ids: studentIds,
      };
      if (instructorId) body.instructor_id = instructorId;
      await apiFetch("/api/v1/studio/model-week/slot", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setSelected(null);
      setReloadToken((n) => n + 1);
    } catch (e) {
      setModalError(e instanceof ApiError ? e.message : "No se pudo guardar la celda.");
    } finally {
      setSaving(false);
    }
  }

  async function clearCell() {
    if (!selected || !roomId || !activityId) return;
    if (!window.confirm("¿Vaciar esta celda de la semana modelo? No afecta abonos ni calendario ya generados.")) return;
    setSaving(true);
    setModalError(null);
    try {
      await apiFetch("/api/v1/studio/model-week/slot", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          room_id: roomId,
          activity_id: activityId,
          weekday: selected.weekday,
          start_time: selected.start_time,
          student_ids: [],
        }),
      });
      setSelected(null);
      setReloadToken((n) => n + 1);
    } catch (e) {
      setModalError(e instanceof ApiError ? e.message : "No se pudo vaciar la celda.");
    } finally {
      setSaving(false);
    }
  }

  const byWeekday = useMemo(() => {
    const map = new Map<number, ModelCell[]>();
    for (const cell of data?.cells ?? []) {
      const list = map.get(cell.weekday) ?? [];
      list.push(cell);
      map.set(cell.weekday, list);
    }
    return map;
  }, [data]);

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-900">Semana modelo</h2>
        <p className="mt-1 text-sm text-slate-600">
          Horario fijo por salón × actividad. Cupo = capacidad del salón. Al abonar se confirman celdas ya asignadas (no toca el calendario operativo).
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <label className="space-y-1 text-sm">
          <span>Sede</span>
          <select className={inputClass} value={siteId} onChange={(e) => { setSiteId(e.target.value); setRoomId(""); }}>
            <option value="">Todas</option>
            {activeSites.map((s) => <option key={s.id} value={s.id}>{asText(s.name)}</option>)}
          </select>
        </label>
        <label className="space-y-1 text-sm">
          <span>Actividad</span>
          <select className={inputClass} value={activityId} onChange={(e) => setActivityId(e.target.value)}>
            <option value="">Elegí…</option>
            {activeActivities.map((a) => <option key={a.id} value={a.id}>{asText(a.name)}</option>)}
          </select>
        </label>
        <label className="space-y-1 text-sm">
          <span>Salón</span>
          <select className={inputClass} value={roomId} onChange={(e) => setRoomId(e.target.value)} disabled={!activityId}>
            <option value="">Elegí…</option>
            {filteredRooms.map((r) => <option key={r.id} value={r.id}>{asText(r.name)}</option>)}
          </select>
        </label>
      </div>

      {error && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {busy && <p className="text-sm text-slate-500">Cargando grilla…</p>}

      {!roomId || !activityId ? (
        <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
          Elegí actividad y salón para ver la semana modelo.
        </p>
      ) : data && !data.cells.length ? (
        <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
          Este salón no tiene horarios configurados, o la duración de la actividad no entra en las ventanas.
        </p>
      ) : data ? (
        <div className="overflow-x-auto">
          <div className="mb-2 text-xs text-slate-500">
            {asText(data.site_name)} · {asText(data.room_name)} · {asText(data.activity_name)} · cupo {data.capacity}
          </div>
          <div className="grid min-w-[720px] grid-cols-7 gap-2">
            {[0, 1, 2, 3, 4, 5, 6].map((wd) => (
              <div key={wd} className="space-y-2">
                <div className="text-center text-xs font-semibold text-slate-700">{WEEKDAY_SHORT[wd]}</div>
                {(byWeekday.get(wd) ?? []).map((cell) => {
                  const filled = Boolean(cell.slot_id);
                  return (
                    <button
                      key={`${cell.weekday}-${cell.start_time}`}
                      type="button"
                      onClick={() => openCell(cell)}
                      className={`w-full rounded-lg border px-2 py-2 text-left text-xs transition ${
                        filled
                          ? "border-brand-200 bg-brand-50 hover:border-brand-400"
                          : "border-slate-200 bg-white hover:border-slate-400"
                      }`}
                    >
                      <div className="font-medium text-slate-800">
                        {toHm(cell.start_time)}–{toHm(cell.end_time)}
                      </div>
                      {filled ? (
                        <>
                          <div className="mt-0.5 text-brand-800">{cell.instructor_name}</div>
                          <div className="text-slate-500">{cell.booked_count}/{cell.capacity}</div>
                        </>
                      ) : (
                        <div className="mt-0.5 text-slate-400">Vacío</div>
                      )}
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {selected && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center" role="dialog" aria-modal="true">
          <div className="flex max-h-[92dvh] w-full max-w-lg flex-col overflow-hidden rounded-xl bg-white shadow-lg">
            <div className="border-b border-slate-100 p-4">
              <h3 className="text-lg font-semibold text-slate-900">
                {WEEKDAY_LABELS[selected.weekday]} · {toHm(selected.start_time)}
              </h3>
              <p className="mt-1 text-xs text-slate-500">Asigná instructor y alumnos fijos (hasta {selected.capacity}).</p>
              {modalError && <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{modalError}</p>}
            </div>
            <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
              <label className="block space-y-1 text-sm">
                <span>Instructor</span>
                <select className={inputClass} value={instructorId} onChange={(e) => setInstructorId(e.target.value)}>
                  <option value="">Elegí…</option>
                  {instructorsForActivity.map((i) => (
                    <option key={i.id} value={i.id}>{asText(i.full_name)}</option>
                  ))}
                </select>
              </label>
              {!instructorsForActivity.length && (
                <p className="text-xs text-slate-500">No hay instructores activos vinculados a esta actividad.</p>
              )}
              <div>
                <div className="mb-1 text-sm font-medium text-slate-800">Alumnos ({studentIds.length}/{selected.capacity})</div>
                <div className="max-h-64 space-y-1 overflow-y-auto rounded-lg border border-slate-200 p-2">
                  {activeStudents.map((s) => (
                    <label key={s.id} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={studentIds.includes(s.id)}
                        disabled={!studentIds.includes(s.id) && studentIds.length >= selected.capacity}
                        onChange={() => toggleStudent(s.id)}
                      />
                      {asText(s.full_name)}
                    </label>
                  ))}
                  {!activeStudents.length && <p className="text-xs text-slate-500">No hay alumnos activos.</p>}
                </div>
              </div>
            </div>
            <div className="flex flex-wrap justify-end gap-2 border-t border-slate-100 p-4">
              {selected.slot_id && (
                <button type="button" className="rounded-lg border border-red-200 px-3 py-2 text-sm text-red-700" disabled={saving} onClick={() => void clearCell()}>
                  Vaciar
                </button>
              )}
              <button type="button" className="rounded-lg border px-3 py-2 text-sm" onClick={() => setSelected(null)}>Cancelar</button>
              <button type="button" className={buttonClass} disabled={saving || (!!studentIds.length && !instructorsForActivity.length)} onClick={() => void saveCell()}>
                {saving ? "Guardando…" : "Guardar"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
