import { useEffect, useState } from "react";
import { ApiError, apiFetch } from "@/services/api";

type Item = Record<string, unknown> & { id: string };

type CalendarHoliday = { id: string; name: string; site_id: string | null };
type CalendarSlot = {
  site_id: string;
  site_name: string;
  room_id: string;
  room_name: string;
  activity_id: string;
  activity_name: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  capacity: number;
};
type CalendarDay = {
  date: string;
  weekday: number;
  is_holiday: boolean;
  holidays: CalendarHoliday[];
  slots: CalendarSlot[];
};
type CalendarAvailability = {
  week_start: string;
  week_end: string;
  days: CalendarDay[];
};

const WEEKDAY_SHORT = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

const inputClass = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm";

function toHm(value: string) {
  return String(value).slice(0, 5);
}

function mondayIso(d: Date) {
  const copy = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const day = copy.getDay(); // 0=Sun
  const diff = day === 0 ? -6 : 1 - day;
  copy.setDate(copy.getDate() + diff);
  return copy;
}

function formatIsoDate(d: Date) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addDays(d: Date, n: number) {
  const copy = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  copy.setDate(copy.getDate() + n);
  return copy;
}

function asText(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

type Props = {
  sites: Item[];
  rooms: Item[];
  activities: Item[];
};

export default function StudioCalendarPanel({ sites, rooms, activities }: Props) {
  const [weekAnchor, setWeekAnchor] = useState(() => mondayIso(new Date()));
  const [siteId, setSiteId] = useState("");
  const [roomId, setRoomId] = useState("");
  const [activityId, setActivityId] = useState("");
  const [data, setData] = useState<CalendarAvailability | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const activeSites = sites.filter((site) => site.active !== false);
  const activeActivities = activities.filter((activity) => activity.active !== false);
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

  useEffect(() => {
    if (!roomId) return;
    const stillValid = rooms.some((room) => {
      if (room.id !== roomId || room.active === false) return false;
      if (siteId && String(room.site_id) !== siteId) return false;
      if (activityId) {
        const activity = activities.find((item) => item.id === activityId);
        const ids = Array.isArray(activity?.room_ids) ? (activity.room_ids as string[]) : [];
        if (!ids.includes(room.id)) return false;
      }
      return true;
    });
    if (!stillValid) setRoomId("");
  }, [roomId, siteId, activityId, rooms, activities]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setBusy(true);
      setError(null);
      try {
        const params = new URLSearchParams({ week_start: formatIsoDate(weekAnchor) });
        if (siteId) params.set("site_id", siteId);
        if (roomId) params.set("room_id", roomId);
        if (activityId) params.set("activity_id", activityId);
        const result = await apiFetch<CalendarAvailability>(
          `/api/v1/studio/calendar/availability?${params}`,
        );
        if (!cancelled) setData(result);
      } catch (e) {
        if (!cancelled) {
          setData(null);
          setError(e instanceof ApiError ? e.message : "No se pudo cargar el calendario.");
        }
      } finally {
        if (!cancelled) setBusy(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [weekAnchor, siteId, roomId, activityId]);

  const weekLabel = data
    ? `${data.week_start} → ${data.week_end}`
    : `${formatIsoDate(weekAnchor)} → ${formatIsoDate(addDays(weekAnchor, 6))}`;

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-medium text-slate-900">Calendario</h2>
          <p className="text-sm text-slate-600">
            Disponibilidad según horario y capacidad del salón, y duración de cada actividad.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            onClick={() => setWeekAnchor((current) => addDays(current, -7))}
          >
            Semana anterior
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            onClick={() => setWeekAnchor(mondayIso(new Date()))}
          >
            Esta semana
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-700 hover:bg-slate-50"
            onClick={() => setWeekAnchor((current) => addDays(current, 7))}
          >
            Semana siguiente
          </button>
        </div>
      </div>

      <p className="text-sm font-medium text-slate-800">{weekLabel}{busy ? " · cargando…" : ""}</p>

      <div className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-3">
        <label className="space-y-1 text-sm text-slate-700">
          <span>Sede</span>
          <select
            className={inputClass}
            value={siteId}
            onChange={(e) => {
              setSiteId(e.target.value);
              setRoomId("");
            }}
          >
            <option value="">Todas</option>
            {activeSites.map((site) => (
              <option key={site.id} value={site.id}>{asText(site.name)}</option>
            ))}
          </select>
        </label>
        <label className="space-y-1 text-sm text-slate-700">
          <span>Actividad</span>
          <select
            className={inputClass}
            value={activityId}
            onChange={(e) => {
              setActivityId(e.target.value);
              setRoomId("");
            }}
          >
            <option value="">Todas</option>
            {activeActivities.map((activity) => (
              <option key={activity.id} value={activity.id}>{asText(activity.name)}</option>
            ))}
          </select>
        </label>
        <label className="space-y-1 text-sm text-slate-700">
          <span>Salón</span>
          <select className={inputClass} value={roomId} onChange={(e) => setRoomId(e.target.value)}>
            <option value="">Todos</option>
            {filteredRooms.map((room) => (
              <option key={room.id} value={room.id}>
                {asText(room.name)}
                {room.site_id ? ` · ${asText(activeSites.find((s) => s.id === room.site_id)?.name ?? room.site_id)}` : ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}

      {!error && data && data.days.every((day) => day.slots.length === 0) && (
        <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">
          No hay franjas disponibles para esta semana con los filtros elegidos. Revisá horarios de salón y actividades vinculadas.
        </p>
      )}

      {data && (
        <div className="overflow-x-auto pb-2">
          <div className="grid min-w-[56rem] grid-cols-7 gap-2">
            {data.days.map((day) => {
              const wd = day.weekday;
              const holidayLabel = day.holidays.map((h) => h.name).join(" · ");
              return (
                <div
                  key={day.date}
                  className={`flex min-h-[14rem] flex-col rounded-xl border p-2 ${
                    day.is_holiday
                      ? "border-amber-200 bg-amber-50/70 opacity-80"
                      : "border-slate-200 bg-white"
                  }`}
                >
                  <div className="mb-2 border-b border-slate-100 pb-2">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {WEEKDAY_SHORT[wd] ?? "—"}
                    </div>
                    <div className="text-sm font-medium text-slate-900">{day.date.slice(8)}/{day.date.slice(5, 7)}</div>
                    {day.is_holiday && (
                      <div className="mt-1 text-[11px] font-medium text-amber-800">
                        Feriado{holidayLabel ? `: ${holidayLabel}` : ""}
                      </div>
                    )}
                  </div>
                  <ul className="flex flex-1 flex-col gap-1.5 overflow-y-auto">
                    {day.slots.map((slot) => (
                      <li
                        key={`${slot.room_id}-${slot.activity_id}-${slot.start_time}`}
                        className="rounded-lg border border-slate-100 bg-slate-50 px-2 py-1.5 text-[11px] leading-snug text-slate-700"
                      >
                        <div className="font-semibold text-slate-900">
                          {toHm(slot.start_time)}–{toHm(slot.end_time)}
                        </div>
                        <div>{slot.activity_name}</div>
                        <div className="text-slate-500">
                          {slot.room_name} · cupo {slot.capacity}
                        </div>
                        {!siteId && <div className="text-slate-400">{slot.site_name}</div>}
                      </li>
                    ))}
                    {!day.slots.length && (
                      <li className="text-[11px] text-slate-400">Sin franjas</li>
                    )}
                  </ul>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <p className="text-xs text-slate-500">
        Solo lectura. La reserva desde el calendario se agregará después.
      </p>
    </section>
  );
}
