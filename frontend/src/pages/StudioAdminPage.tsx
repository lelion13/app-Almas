import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { ApiError, apiFetch } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";

type Item = Record<string, unknown> & { id: string };
/** Local draft slot; `key` is client-only until saved. */
type HourSlot = { key: string; weekday: number; open_time: string; close_time: string };
type Tab =
  | "sites" | "rooms" | "activities" | "instructors" | "students" | "series"
  | "sessions" | "holidays" | "products" | "packs" | "audit";

const WEEKDAY_LABELS = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];

function toHm(value: string | null | undefined, fallback = "08:00") {
  if (!value) return fallback;
  return String(value).slice(0, 5);
}

function timeToMinutes(value: string) {
  const [h, m] = value.split(":").map(Number);
  return h * 60 + m;
}

/** Half-open [open, close) overlap for HH:MM strings. */
function rangesOverlap(aOpen: string, aClose: string, bOpen: string, bClose: string) {
  return timeToMinutes(aOpen) < timeToMinutes(bClose) && timeToMinutes(bOpen) < timeToMinutes(aClose);
}

function newSlotKey() {
  return `slot-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

const TABS: Array<[Tab, string]> = [
  ["sites", "Sedes"], ["rooms", "Salones"], ["activities", "Actividades"],
  ["instructors", "Instructores"], ["students", "Alumnos"], ["series", "Series"],
  ["sessions", "Sesiones"], ["holidays", "Feriados"], ["products", "Productos"],
  ["packs", "Paquetes"], ["audit", "Auditoría"],
];

const inputClass = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm";
const buttonClass = "rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800 disabled:opacity-60";

function asText(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function List({ items, fields, empty = "No hay registros." }: { items: Item[]; fields: string[]; empty?: string }) {
  if (!items.length) return <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">{empty}</p>;
  return (
    <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
      {items.map((item) => (
        <li key={item.id} className="px-4 py-3 text-sm">
          <div className="font-medium text-slate-900">{asText(item[fields[0]])}</div>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
            {fields.slice(1).map((field) => <span key={field}>{field.replaceAll("_", " ")}: {asText(item[field])}</span>)}
          </div>
        </li>
      ))}
    </ul>
  );
}

function Field({ label, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return <label className="space-y-1 text-sm text-slate-700"><span>{label}</span><input className={inputClass} {...props} /></label>;
}

export default function StudioAdminPage() {
  const { me } = useAuth();
  const [tab, setTab] = useState<Tab>("sites");
  const [data, setData] = useState<Record<string, Item[]>>({});
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editRoom, setEditRoom] = useState<Item | null>(null);
  const [hoursRoom, setHoursRoom] = useState<Item | null>(null);
  const [hourSlots, setHourSlots] = useState<HourSlot[]>([]);
  const [slotDraft, setSlotDraft] = useState({ weekday: "1", open_time: "08:00", close_time: "12:00" });
  const [editDraft, setEditDraft] = useState({
    site_id: "", share_space: false, share_room_id: "", name: "", capacity: "8", duration: "60", active: true,
  });
  const [editActivity, setEditActivity] = useState<Item | null>(null);
  const [editActivityDraft, setEditActivityDraft] = useState({
    name: "", level: "inicial", duration: "60", active: true, room_ids: [] as string[],
  });
  const [createRoomIds, setCreateRoomIds] = useState<string[]>([]);
  const [createInstructorActivityIds, setCreateInstructorActivityIds] = useState<string[]>([]);
  const [editInstructor, setEditInstructor] = useState<Item | null>(null);
  const [editInstructorDraft, setEditInstructorDraft] = useState({
    full_name: "", email: "", phone: "", active: true, activity_ids: [] as string[], password: "",
  });
  const [editInstructorPasswordTouched, setEditInstructorPasswordTouched] = useState(false);

  const value = (key: string) => values[key] ?? "";
  const setValue = (key: string, next: string) => setValues((current) => ({ ...current, [key]: next }));
  const list = (key: string) => data[key] ?? [];
  const id = (key: string) => value(key);
  const query = (path: string, params: Record<string, string>) => {
    const pairs = Object.entries(params).filter(([, current]) => current);
    return pairs.length ? `${path}?${new URLSearchParams(pairs)}` : path;
  };

  async function load(key: string, path: string) {
    try {
      const items = await apiFetch<Item[]>(path);
      setData((current) => ({ ...current, [key]: items }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudieron cargar los datos.");
    }
  }

  async function loadTab(next = tab) {
    const paths: Partial<Record<Tab, string>> = {
      sites: "/api/v1/studio/sites",
      rooms: query("/api/v1/studio/rooms", { site_id: id("roomSite") }),
      activities: "/api/v1/studio/activities",
      instructors: "/api/v1/studio/instructors",
      students: "/api/v1/studio/students",
      series: "/api/v1/studio/series",
      sessions: "/api/v1/studio/sessions",
      holidays: "/api/v1/studio/holidays",
      products: "/api/v1/studio/pack-products",
      packs: query("/api/v1/studio/student-packs", { student_id: id("packStudent") }),
      audit: "/api/v1/studio/audit",
    };
    if (paths[next]) await load(next, paths[next]!);
  }

  useEffect(() => { void loadTab(); }, [tab]);
  useEffect(() => {
    void Promise.all([
      load("sites", "/api/v1/studio/sites"), load("activities", "/api/v1/studio/activities"),
      load("instructors", "/api/v1/studio/instructors"), load("students", "/api/v1/studio/students"),
      load("products", "/api/v1/studio/pack-products"), load("roomsAll", "/api/v1/studio/rooms"),
      load("packs", "/api/v1/studio/student-packs"), load("series", "/api/v1/studio/series"),
    ]);
  }, []);

  if (me?.role !== "admin") return <Navigate to="/" replace />;

  async function refreshRoomsCatalog() {
    await load("roomsAll", "/api/v1/studio/rooms");
    if (tab === "rooms") await loadTab("rooms");
  }

  async function submit(path: string, body: unknown, success: string, reload = tab) {
    setBusy(true); setError(null); setNotice(null);
    try {
      await apiFetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      setNotice(success);
      await loadTab(reload);
      if (path.includes("/studio/rooms")) await load("roomsAll", "/api/v1/studio/rooms");
      if (path.includes("/studio/sites")) await load("sites", "/api/v1/studio/sites");
      if (path.includes("/studio/activities")) await load("activities", "/api/v1/studio/activities");
      if (path.includes("/studio/instructors")) await load("instructors", "/api/v1/studio/instructors");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo guardar.");
    } finally { setBusy(false); }
  }

  const form = (onSubmit: (e: FormEvent) => void, children: React.ReactNode) => (
    <form onSubmit={onSubmit} className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-2">
      {children}
      <div className="sm:col-span-2"><button type="submit" className={buttonClass} disabled={busy}>{busy ? "Guardando…" : "Guardar"}</button></div>
    </form>
  );

  const siteName = (siteId: unknown) => {
    const site = list("sites").find((item) => item.id === siteId);
    return site ? asText(site.name) : asText(siteId);
  };
  const roomName = (roomId: unknown) => {
    if (!roomId) return "—";
    const room = list("roomsAll").find((item) => item.id === roomId) ?? list("rooms").find((item) => item.id === roomId);
    return room ? asText(room.name) : asText(roomId);
  };
  const roomsForSiteExcept = (siteId: string, exceptId?: string) =>
    list("roomsAll").filter((room) => {
      if (siteId && String(room.site_id) !== siteId) return false;
      if (exceptId && room.id === exceptId) return false;
      if (room.active === false) return false;
      return true;
    });
  const activeRooms = list("roomsAll").filter((room) => room.active !== false);
  const activeSites = list("sites").filter((site) => site.active !== false);
  const activeActivities = list("activities").filter((activity) => activity.active !== false);
  const roomsForSeries = () => {
    const siteId = value("seriesSite");
    const activityId = value("seriesActivity");
    const activity = list("activities").find((item) => item.id === activityId);
    const linked = new Set(
      Array.isArray(activity?.room_ids) ? (activity.room_ids as string[]).map(String) : [],
    );
    return activeRooms.filter((room) => {
      if (siteId && String(room.site_id) !== siteId) return false;
      if (activityId && !linked.has(room.id)) return false;
      return true;
    });
  };
  const activityRoomLabels = (activity: Item) => {
    const ids = Array.isArray(activity.room_ids) ? (activity.room_ids as string[]) : [];
    if (!ids.length) return "sin salones (asigná en Editar)";
    return ids.map((rid) => {
      const room = list("roomsAll").find((item) => item.id === rid);
      if (!room) return asText(rid);
      return `${asText(room.name)} (${siteName(room.site_id)})`;
    }).join(" · ");
  };
  const toggleRoomId = (ids: string[], roomId: string) => (
    ids.includes(roomId) ? ids.filter((id) => id !== roomId) : [...ids, roomId]
  );
  const toggleActivityId = (ids: string[], activityId: string) => (
    ids.includes(activityId) ? ids.filter((id) => id !== activityId) : [...ids, activityId]
  );
  const instructorActivityLabels = (instructor: Item) => {
    const ids = Array.isArray(instructor.activity_ids) ? (instructor.activity_ids as string[]) : [];
    if (!ids.length) return "sin actividades";
    return ids.map((aid) => {
      const activity = list("activities").find((item) => item.id === aid);
      return activity ? asText(activity.name) : asText(aid);
    }).join(" · ");
  };
  const selects = {
    site: activeSites, room: list("roomsAll"), activity: activeActivities,
    instructor: list("instructors"), student: list("students"), product: list("products"), pack: list("packs"),
  };
  const allSites = list("sites");

  function closeEditActivity() {
    setEditActivity(null);
    setModalError(null);
  }

  function openEditActivity(activity: Item) {
    setEditActivity(activity);
    setEditActivityDraft({
      name: String(activity.name ?? ""),
      level: String(activity.level ?? "inicial"),
      duration: String(activity.default_duration_minutes ?? "60"),
      active: activity.active !== false,
      room_ids: Array.isArray(activity.room_ids) ? (activity.room_ids as string[]).map(String) : [],
    });
    setError(null);
    setModalError(null);
  }

  async function saveEditActivity() {
    if (!editActivity) return;
    if (editActivityDraft.room_ids.length < 1) {
      setModalError("Elegí al menos un salón.");
      return;
    }
    setBusy(true); setModalError(null); setNotice(null);
    try {
      await apiFetch(`/api/v1/studio/activities/${editActivity.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editActivityDraft.name.trim(),
          level: editActivityDraft.level.trim() || "inicial",
          default_duration_minutes: Number(editActivityDraft.duration),
          active: editActivityDraft.active,
          room_ids: editActivityDraft.room_ids,
        }),
      });
      setNotice("Actividad actualizada.");
      closeEditActivity();
      await load("activities", "/api/v1/studio/activities");
      if (tab === "activities") await loadTab("activities");
    } catch (e) {
      setModalError(e instanceof ApiError ? e.message : "No se pudo actualizar la actividad.");
    } finally {
      setBusy(false);
    }
  }

  async function softDeleteActivity(activity: Item) {
    if (!window.confirm(`¿Desactivar la actividad "${asText(activity.name)}"? El historial se mantiene.`)) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      await apiFetch(`/api/v1/studio/activities/${activity.id}`, { method: "DELETE" });
      setNotice("Actividad desactivada.");
      await load("activities", "/api/v1/studio/activities");
      if (tab === "activities") await loadTab("activities");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo desactivar la actividad.");
    } finally {
      setBusy(false);
    }
  }

  async function createActivitySubmit(e: FormEvent) {
    e.preventDefault();
    if (createRoomIds.length < 1) {
      setError("Elegí al menos un salón para la actividad.");
      return;
    }
    setBusy(true); setError(null); setNotice(null);
    try {
      await apiFetch("/api/v1/studio/activities", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: value("activityName").trim(),
          level: value("activityLevel") || "inicial",
          default_duration_minutes: Number(value("activityDuration") || 60),
          room_ids: createRoomIds,
        }),
      });
      setNotice("Actividad creada.");
      setCreateRoomIds([]);
      setValue("activityName", "");
      setValue("activityLevel", "");
      setValue("activityDuration", "");
      await load("activities", "/api/v1/studio/activities");
      if (tab === "activities") await loadTab("activities");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear la actividad.");
    } finally {
      setBusy(false);
    }
  }

  function RoomPickers({
    selected,
    onChange,
  }: {
    selected: string[];
    onChange: (next: string[]) => void;
  }) {
    const roomsForPicker = list("roomsAll").filter(
      (room) => room.active !== false || selected.includes(room.id),
    );
    const bySite = allSites
      .map((site) => ({
        site,
        rooms: roomsForPicker.filter((room) => String(room.site_id) === site.id),
      }))
      .filter((group) => group.rooms.length > 0);
    if (!bySite.length) {
      return <p className="text-sm text-amber-800">No hay salones activos. Creá uno en <strong>Salones</strong>.</p>;
    }
    return (
      <div className="space-y-3 sm:col-span-2">
        <p className="text-sm font-medium text-slate-700">Salones (uno o más)</p>
        {bySite.map(({ site, rooms }) => (
          <div key={site.id} className="rounded-lg border border-slate-200 bg-white p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{asText(site.name)}</p>
            <div className="flex flex-col gap-2">
              {rooms.map((room) => (
                <label key={room.id} className="flex items-center gap-2 text-sm text-slate-800">
                  <input
                    type="checkbox"
                    checked={selected.includes(room.id)}
                    onChange={() => onChange(toggleRoomId(selected, room.id))}
                  />
                  {asText(room.name)}
                  {room.active === false ? <span className="text-xs text-amber-700">(inactivo)</span> : null}
                  <span className="text-xs text-slate-500">cap. {asText(room.capacity)}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  function ActivityPickers({
    selected,
    onChange,
  }: {
    selected: string[];
    onChange: (next: string[]) => void;
  }) {
    const activitiesForPicker = list("activities").filter(
      (activity) => activity.active !== false || selected.includes(activity.id),
    );
    if (!activitiesForPicker.length) {
      return <p className="text-sm text-amber-800">No hay actividades. Creá una en <strong>Actividades</strong>.</p>;
    }
    return (
      <div className="space-y-2 sm:col-span-2">
        <p className="text-sm font-medium text-slate-700">Actividades (opcional)</p>
        <div className="rounded-lg border border-slate-200 bg-white p-3">
          <div className="flex flex-col gap-2">
            {activitiesForPicker.map((activity) => (
              <label key={activity.id} className="flex items-center gap-2 text-sm text-slate-800">
                <input
                  type="checkbox"
                  checked={selected.includes(activity.id)}
                  onChange={() => onChange(toggleActivityId(selected, activity.id))}
                />
                {asText(activity.name)}
                {activity.active === false ? <span className="text-xs text-amber-700">(inactiva)</span> : null}
                <span className="text-xs text-slate-500">nivel {asText(activity.level)}</span>
              </label>
            ))}
          </div>
        </div>
      </div>
    );
  }

  function closeEditInstructor() {
    setEditInstructor(null);
    setEditInstructorPasswordTouched(false);
    setModalError(null);
  }

  function openEditInstructor(instructor: Item) {
    setEditInstructor(instructor);
    setEditInstructorDraft({
      full_name: String(instructor.full_name ?? ""),
      email: String(instructor.email ?? ""),
      phone: String(instructor.phone ?? ""),
      active: instructor.active !== false,
      activity_ids: Array.isArray(instructor.activity_ids) ? (instructor.activity_ids as string[]).map(String) : [],
      password: "",
    });
    setEditInstructorPasswordTouched(false);
    // Clear create form so browser autofill (admin login) does not leak into edits.
    setValue("instructorEmail", "");
    setValue("instructorPassword", "");
    setError(null);
    setModalError(null);
  }

  async function saveEditInstructor() {
    if (!editInstructor) return;
    const email = editInstructorDraft.email.trim();
    const password = editInstructorPasswordTouched ? editInstructorDraft.password : "";
    if (password && !email) {
      setModalError("Indicá el email para crear o actualizar el acceso.");
      return;
    }
    setBusy(true); setModalError(null); setNotice(null);
    try {
      const body: Record<string, unknown> = {
        full_name: editInstructorDraft.full_name.trim(),
        email: email || null,
        phone: editInstructorDraft.phone.trim() || null,
        active: editInstructorDraft.active,
        activity_ids: editInstructorDraft.activity_ids,
      };
      if (password) body.password = password;
      await apiFetch(`/api/v1/studio/instructors/${editInstructor.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setNotice("Instructor actualizado.");
      closeEditInstructor();
      await load("instructors", "/api/v1/studio/instructors");
      if (tab === "instructors") await loadTab("instructors");
    } catch (e) {
      setModalError(e instanceof ApiError ? e.message : "No se pudo actualizar el instructor.");
    } finally {
      setBusy(false);
    }
  }

  async function softDeleteInstructor(instructor: Item) {
    if (!window.confirm(`¿Desactivar al instructor "${asText(instructor.full_name)}"? El historial se mantiene.`)) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      await apiFetch(`/api/v1/studio/instructors/${instructor.id}`, { method: "DELETE" });
      setNotice("Instructor desactivado.");
      await load("instructors", "/api/v1/studio/instructors");
      if (tab === "instructors") await loadTab("instructors");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo desactivar el instructor.");
    } finally {
      setBusy(false);
    }
  }

  async function createInstructorSubmit(e: FormEvent) {
    e.preventDefault();
    const email = value("instructorEmail").trim();
    const password = value("instructorPassword");
    if (password && !email) {
      setError("Indicá el email para habilitar el acceso a la app.");
      return;
    }
    setBusy(true); setError(null); setNotice(null);
    try {
      const body: Record<string, unknown> = {
        full_name: value("instructorName").trim(),
        email: email || null,
        phone: value("instructorPhone").trim() || null,
        activity_ids: createInstructorActivityIds,
      };
      if (password) body.password = password;
      await apiFetch("/api/v1/studio/instructors", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setNotice("Instructor creado.");
      setCreateInstructorActivityIds([]);
      setValue("instructorName", "");
      setValue("instructorEmail", "");
      setValue("instructorPhone", "");
      setValue("instructorPassword", "");
      await load("instructors", "/api/v1/studio/instructors");
      if (tab === "instructors") await loadTab("instructors");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el instructor.");
    } finally {
      setBusy(false);
    }
  }

  async function patchSite(siteId: string, body: Record<string, unknown>, success: string) {
    setBusy(true); setError(null); setNotice(null);
    try {
      await apiFetch(`/api/v1/studio/sites/${siteId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setNotice(success);
      await load("sites", "/api/v1/studio/sites");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo guardar la sede.");
    } finally {
      setBusy(false);
    }
  }

  function closeEditRoom() {
    setEditRoom(null);
    setModalError(null);
  }

  function closeHoursRoom() {
    setHoursRoom(null);
    setHourSlots([]);
    setModalError(null);
  }

  async function openEditRoom(room: Item) {
    setEditRoom(room);
    setEditDraft({
      site_id: String(room.site_id ?? ""),
      share_space: Boolean(room.shares_space_with_room_id),
      share_room_id: room.shares_space_with_room_id ? String(room.shares_space_with_room_id) : "",
      name: String(room.name ?? ""),
      capacity: String(room.capacity ?? "8"),
      duration: String(room.default_class_duration_minutes ?? "60"),
      active: room.active !== false,
    });
    setError(null);
    setModalError(null);
  }

  async function saveEditRoom() {
    if (!editRoom) return;
    if (editDraft.share_space && !editDraft.share_room_id) {
      setModalError("Elegí el salón con el que comparte el espacio.");
      return;
    }
    setBusy(true); setModalError(null); setNotice(null);
    try {
      await apiFetch(`/api/v1/studio/rooms/${editRoom.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          site_id: editDraft.site_id,
          shares_space_with_room_id: editDraft.share_space ? editDraft.share_room_id : null,
          name: editDraft.name.trim(),
          capacity: Number(editDraft.capacity),
          default_class_duration_minutes: Number(editDraft.duration),
          active: editDraft.active,
        }),
      });
      setNotice("Salón actualizado.");
      closeEditRoom();
      await refreshRoomsCatalog();
    } catch (e) {
      setModalError(e instanceof ApiError ? e.message : "No se pudo actualizar el salón.");
    } finally {
      setBusy(false);
    }
  }

  async function openHoursRoom(room: Item) {
    setHoursRoom(room);
    setError(null);
    setModalError(null);
    setSlotDraft({ weekday: "1", open_time: "08:00", close_time: "12:00" });
    try {
      const res = await apiFetch<{ room_id: string; slots: Array<{ id?: string; weekday: number; open_time: string; close_time: string }> }>(
        `/api/v1/studio/rooms/${room.id}/hours`,
      );
      const slots = (res.slots ?? [])
        .map((s) => ({
          key: s.id ?? newSlotKey(),
          weekday: s.weekday,
          open_time: toHm(s.open_time),
          close_time: toHm(s.close_time, "21:00"),
        }))
        .sort((a, b) => a.weekday - b.weekday || timeToMinutes(a.open_time) - timeToMinutes(b.open_time));
      setHourSlots(slots);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudieron cargar los horarios.");
      closeHoursRoom();
    }
  }

  function addHourSlot() {
    setModalError(null);
    const weekday = Number(slotDraft.weekday);
    const open_time = slotDraft.open_time;
    const close_time = slotDraft.close_time;
    if (!Number.isInteger(weekday) || weekday < 0 || weekday > 6) {
      setModalError("Elegí un día válido.");
      return;
    }
    if (!open_time || !close_time) {
      setModalError("Completá el rango horario.");
      return;
    }
    if (timeToMinutes(close_time) <= timeToMinutes(open_time)) {
      setModalError("La hora de fin debe ser posterior a la de inicio.");
      return;
    }
    const overlaps = hourSlots.some(
      (s) => s.weekday === weekday && rangesOverlap(open_time, close_time, s.open_time, s.close_time),
    );
    if (overlaps) {
      setModalError(`La franja se superpone con otra del mismo día (${WEEKDAY_LABELS[weekday]}).`);
      return;
    }
    setHourSlots((rows) =>
      [...rows, { key: newSlotKey(), weekday, open_time, close_time }].sort(
        (a, b) => a.weekday - b.weekday || timeToMinutes(a.open_time) - timeToMinutes(b.open_time),
      ),
    );
  }

  function removeHourSlot(key: string) {
    setModalError(null);
    setHourSlots((rows) => rows.filter((s) => s.key !== key));
  }

  async function saveHoursRoom() {
    if (!hoursRoom) return;
    setBusy(true); setModalError(null); setNotice(null);
    try {
      const slots = hourSlots.map((s) => ({
        weekday: s.weekday,
        open_time: s.open_time.length === 5 ? `${s.open_time}:00` : s.open_time,
        close_time: s.close_time.length === 5 ? `${s.close_time}:00` : s.close_time,
      }));
      await apiFetch(`/api/v1/studio/rooms/${hoursRoom.id}/hours`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slots }),
      });
      setNotice("Horarios guardados.");
      closeHoursRoom();
    } catch (e) {
      setModalError(e instanceof ApiError ? e.message : "No se pudieron guardar los horarios.");
    } finally {
      setBusy(false);
    }
  }

  const Select = ({ label, field, items, required = true, onChangeExtra }: {
    label: string; field: string; items: Item[]; required?: boolean;
    onChangeExtra?: (next: string) => void;
  }) => (
    <label className="space-y-1 text-sm text-slate-700"><span>{label}</span>
      <select
        className={inputClass}
        value={value(field)}
        onChange={(e) => {
          setValue(field, e.target.value);
          onChangeExtra?.(e.target.value);
        }}
        required={required}
      >
        <option value="">Seleccionar…</option>
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {asText(item.name ?? item.full_name ?? item.id)}
            {item.site_id ? ` · ${siteName(item.site_id)}` : ""}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-semibold text-slate-900">Estudio</h1><p className="mt-1 text-sm text-slate-600">Administrá la operación diaria del estudio.</p></div>
      <nav className="flex gap-2 overflow-x-auto pb-1" aria-label="Secciones de Estudio">
        {TABS.map(([key, label]) => <button type="button" key={key} onClick={() => { setTab(key); setError(null); setNotice(null); }} className={`shrink-0 rounded-lg px-3 py-2 text-sm font-medium ${tab === key ? "bg-brand-700 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}>{label}</button>)}
      </nav>
      {error && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</p>}
      {notice && <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{notice}</p>}

      {tab === "sites" && <section className="space-y-4">
        {form((e) => {
          e.preventDefault();
          void submit("/api/v1/studio/sites", {
            name: value("siteName"),
            address: value("siteAddress") || null,
            active: value("siteActive") !== "off",
            maps_url: value("siteMapsUrl") || null,
          }, "Sede creada.");
        }, <>
          <Field label="Nombre" value={value("siteName")} onChange={(e) => setValue("siteName", e.target.value)} required />
          <Field label="Dirección (opcional)" value={value("siteAddress")} onChange={(e) => setValue("siteAddress", e.target.value)} />
          <Field label="Link Google Maps (opcional)" type="url" placeholder="https://maps.google.com/..." value={value("siteMapsUrl")} onChange={(e) => setValue("siteMapsUrl", e.target.value)} />
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={value("siteActive") !== "off"} onChange={(e) => setValue("siteActive", e.target.checked ? "on" : "off")} />
            Activa
          </label>
        </>)}
        {allSites.length === 0 ? (
          <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">No hay sedes.</p>
        ) : (
          <ul className="space-y-3">
            {allSites.map((site) => {
              const nameVal = values[`edit-${site.id}-name`] ?? String(site.name ?? "");
              const addressVal = values[`edit-${site.id}-address`] ?? (site.address == null ? "" : String(site.address));
              const mapsVal = values[`edit-${site.id}-maps_url`] ?? (site.maps_url == null ? "" : String(site.maps_url));
              const activeVal = values[`edit-${site.id}-active`] !== undefined
                ? values[`edit-${site.id}-active`] === "on"
                : site.active !== false;
              return (
                <li key={site.id} className={`rounded-xl border p-4 ${site.active === false ? "border-slate-200 bg-slate-50 opacity-90" : "border-slate-200 bg-white"}`}>
                  <div className="mb-3 flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-slate-900">{asText(site.name)}</span>
                    {site.active === false && <span className="rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-700">Inactiva</span>}
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Field label="Nombre" value={nameVal} onChange={(e) => setValue(`edit-${site.id}-name`, e.target.value)} required />
                    <Field label="Dirección" value={addressVal} onChange={(e) => setValue(`edit-${site.id}-address`, e.target.value)} />
                    <Field label="Link Google Maps" type="url" value={mapsVal} onChange={(e) => setValue(`edit-${site.id}-maps_url`, e.target.value)} placeholder="https://maps.google.com/..." />
                    <label className="flex items-center gap-2 self-end pb-2 text-sm text-slate-700">
                      <input
                        type="checkbox"
                        checked={activeVal}
                        onChange={(e) => setValue(`edit-${site.id}-active`, e.target.checked ? "on" : "off")}
                      />
                      Activa
                    </label>
                  </div>
                  <div className="mt-3">
                    <button
                      type="button"
                      className={buttonClass}
                      disabled={busy}
                      onClick={() => void patchSite(site.id, {
                        name: nameVal.trim(),
                        address: addressVal.trim() || null,
                        maps_url: mapsVal.trim() || null,
                        active: activeVal,
                      }, "Sede actualizada.")}
                    >
                      {busy ? "Guardando…" : "Guardar"}
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>}

      {tab === "rooms" && <section className="space-y-4">
        {form((e) => {
          e.preventDefault();
          if (value("newRoomShares") === "on" && !id("newRoomSharePeer")) {
            setError("Elegí el salón con el que comparte el espacio.");
            return;
          }
          void submit("/api/v1/studio/rooms", {
            site_id: id("newRoomSite"),
            shares_space_with_room_id: value("newRoomShares") === "on" ? id("newRoomSharePeer") : null,
            name: value("roomName"),
            capacity: Number(value("roomCapacity")),
            default_class_duration_minutes: Number(value("roomDuration") || 60),
          }, "Salón creado.");
        }, <>
          <Select
            label="Sede"
            field="newRoomSite"
            items={selects.site}
            onChangeExtra={() => setValue("newRoomSharePeer", "")}
          />
          <label className="flex items-center gap-2 text-sm text-slate-700 sm:col-span-2">
            <input
              type="checkbox"
              checked={value("newRoomShares") === "on"}
              onChange={(e) => {
                setValue("newRoomShares", e.target.checked ? "on" : "off");
                if (!e.target.checked) setValue("newRoomSharePeer", "");
              }}
            />
            Comparte espacio físico con otro salón
          </label>
          {value("newRoomShares") === "on" && (
            <label className="space-y-1 text-sm text-slate-700 sm:col-span-2">
              <span>Salón con el que comparte</span>
              <select className={inputClass} value={value("newRoomSharePeer")} onChange={(e) => setValue("newRoomSharePeer", e.target.value)} required>
                <option value="">Seleccionar…</option>
                {roomsForSiteExcept(value("newRoomSite")).map((room) => (
                  <option key={room.id} value={room.id}>{asText(room.name)}</option>
                ))}
              </select>
            </label>
          )}
          <Field label="Nombre" value={value("roomName")} onChange={(e) => setValue("roomName", e.target.value)} required />
          <Field label="Capacidad" type="number" min="1" value={value("roomCapacity")} onChange={(e) => setValue("roomCapacity", e.target.value)} required />
          <Field label="Duración de clase (minutos)" type="number" min="1" value={value("roomDuration") || "60"} onChange={(e) => setValue("roomDuration", e.target.value)} required />
        </>)}
        <div className="flex flex-wrap gap-2">
          <select
            className={inputClass}
            value={value("roomSite")}
            onChange={(e) => {
              setValue("roomSite", e.target.value);
              void load("rooms", query("/api/v1/studio/rooms", { site_id: e.target.value }));
            }}
          >
            <option value="">Todas las sedes</option>
            {list("sites").map((site) => <option key={site.id} value={site.id}>{asText(site.name)}{site.active === false ? " (inactiva)" : ""}</option>)}
          </select>
          <button type="button" className="rounded-lg border px-3 text-sm" onClick={() => void refreshRoomsCatalog()}>Actualizar</button>
        </div>
        {list("rooms").length === 0 ? (
          <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">No hay salones{(value("roomSite") ? " para esta sede" : "")}.</p>
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {list("rooms").map((room) => (
              <li key={room.id} className="flex flex-col gap-3 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="font-medium text-slate-900">{asText(room.name)}{room.active === false ? " · inactivo" : ""}</div>
                  <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
                    <span>sede: {siteName(room.site_id)}</span>
                    {room.shares_space_with_room_id ? (
                      <span>comparte espacio con: {roomName(room.shares_space_with_room_id)}</span>
                    ) : (
                      <span>espacio propio</span>
                    )}
                    <span>capacidad: {asText(room.capacity)}</span>
                    <span>duración: {asText(room.default_class_duration_minutes ?? 60)} min</span>
                  </div>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button type="button" className="rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-700" onClick={() => void openEditRoom(room)}>Editar</button>
                  <button type="button" className="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-600" onClick={() => void openHoursRoom(room)}>Horarios</button>
                </div>
              </li>
            ))}
          </ul>
        )}
        {editRoom && (
          <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center" role="dialog" aria-modal="true" aria-label="Editar salón">
            <div className="max-h-[90dvh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-4 shadow-lg">
              <h3 className="text-lg font-semibold text-slate-900">Editar salón</h3>
              {modalError && (
                <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
                  {modalError}
                </p>
              )}
              <div className="mt-3 grid gap-3">
                <label className="space-y-1 text-sm"><span>Sede</span>
                  <select
                    className={inputClass}
                    value={editDraft.site_id}
                    onChange={(e) => {
                      const nextSite = e.target.value;
                      setModalError(null);
                      setEditDraft((d) => {
                        const stillValid = roomsForSiteExcept(nextSite, editRoom.id).some((r) => r.id === d.share_room_id);
                        return { ...d, site_id: nextSite, share_room_id: stillValid ? d.share_room_id : "", share_space: stillValid ? d.share_space : false };
                      });
                    }}
                  >
                    {list("sites").map((site) => <option key={site.id} value={site.id}>{asText(site.name)}</option>)}
                  </select>
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={editDraft.share_space}
                    onChange={(e) => {
                      setModalError(null);
                      setEditDraft((d) => ({ ...d, share_space: e.target.checked, share_room_id: e.target.checked ? d.share_room_id : "" }));
                    }}
                  />
                  Comparte espacio físico con otro salón
                </label>
                {editDraft.share_space && (
                  <label className="space-y-1 text-sm"><span>Salón con el que comparte</span>
                    <select
                      className={inputClass}
                      value={editDraft.share_room_id}
                      onChange={(e) => { setModalError(null); setEditDraft((d) => ({ ...d, share_room_id: e.target.value })); }}
                    >
                      <option value="">Seleccionar…</option>
                      {roomsForSiteExcept(editDraft.site_id, editRoom.id).map((room) => (
                        <option key={room.id} value={room.id}>{asText(room.name)}</option>
                      ))}
                    </select>
                  </label>
                )}
                <Field label="Nombre" value={editDraft.name} onChange={(e) => { setModalError(null); setEditDraft((d) => ({ ...d, name: e.target.value })); }} />
                <Field label="Capacidad" type="number" min="1" value={editDraft.capacity} onChange={(e) => { setModalError(null); setEditDraft((d) => ({ ...d, capacity: e.target.value })); }} />
                <Field label="Duración de clase (minutos)" type="number" min="1" value={editDraft.duration} onChange={(e) => { setModalError(null); setEditDraft((d) => ({ ...d, duration: e.target.value })); }} />
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={editDraft.active} onChange={(e) => { setModalError(null); setEditDraft((d) => ({ ...d, active: e.target.checked })); }} /> Activo</label>
              </div>
              <div className="mt-4 flex justify-end gap-2">
                <button type="button" className="rounded-lg border px-3 py-2 text-sm" onClick={closeEditRoom}>Cancelar</button>
                <button type="button" className={buttonClass} disabled={busy} onClick={() => void saveEditRoom()}>{busy ? "Guardando…" : "Guardar"}</button>
              </div>
            </div>
          </div>
        )}
        {hoursRoom && (
          <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center" role="dialog" aria-modal="true" aria-label="Horarios del salón">
            <div className="flex max-h-[90dvh] w-full max-w-lg flex-col overflow-hidden rounded-xl bg-white shadow-lg">
              <div className="border-b border-slate-100 p-4">
                <h3 className="text-lg font-semibold text-slate-900">Horarios · {asText(hoursRoom.name)}</h3>
                <p className="mt-1 text-xs text-slate-500">
                  Podés cargar varias franjas el mismo día (p. ej. mañana y tarde). Si este salón comparte espacio con otro, no pueden pisarse. Sin franjas no se pueden crear series.
                </p>
                {modalError && (
                  <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
                    {modalError}
                  </p>
                )}
                <div className="mt-3 grid gap-2 sm:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)_minmax(0,0.9fr)_auto] sm:items-end">
                  <label className="space-y-1 text-sm text-slate-700">
                    <span>Día</span>
                    <select
                      className={inputClass}
                      value={slotDraft.weekday}
                      onChange={(e) => { setModalError(null); setSlotDraft((d) => ({ ...d, weekday: e.target.value })); }}
                    >
                      {WEEKDAY_LABELS.map((label, weekday) => (
                        <option key={weekday} value={String(weekday)}>{label}</option>
                      ))}
                    </select>
                  </label>
                  <label className="space-y-1 text-sm text-slate-700">
                    <span>Desde</span>
                    <input
                      type="time"
                      className={inputClass}
                      value={slotDraft.open_time}
                      onChange={(e) => { setModalError(null); setSlotDraft((d) => ({ ...d, open_time: e.target.value })); }}
                    />
                  </label>
                  <label className="space-y-1 text-sm text-slate-700">
                    <span>Hasta</span>
                    <input
                      type="time"
                      className={inputClass}
                      value={slotDraft.close_time}
                      onChange={(e) => { setModalError(null); setSlotDraft((d) => ({ ...d, close_time: e.target.value })); }}
                    />
                  </label>
                  <button
                    type="button"
                    className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-100"
                    onClick={addHourSlot}
                  >
                    Agregar
                  </button>
                </div>
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto p-4">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">Franjas cargadas</p>
                {hourSlots.length === 0 ? (
                  <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-center text-sm text-slate-500">
                    Todavía no hay franjas. Agregá día y rango arriba.
                  </p>
                ) : (
                  <div className="overflow-x-auto rounded-lg border border-slate-200">
                    <table className="w-full min-w-[280px] text-left text-sm">
                      <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                        <tr>
                          <th className="px-3 py-2 font-medium">Día</th>
                          <th className="px-3 py-2 font-medium">Desde</th>
                          <th className="px-3 py-2 font-medium">Hasta</th>
                          <th className="px-3 py-2 font-medium"><span className="sr-only">Quitar</span></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 bg-white">
                        {hourSlots.map((slot) => (
                          <tr key={slot.key}>
                            <td className="px-3 py-2 font-medium text-slate-900">{WEEKDAY_LABELS[slot.weekday]}</td>
                            <td className="px-3 py-2 text-slate-700">{slot.open_time}</td>
                            <td className="px-3 py-2 text-slate-700">{slot.close_time}</td>
                            <td className="px-3 py-2 text-right">
                              <button
                                type="button"
                                className="text-xs font-medium text-red-700 hover:underline"
                                onClick={() => removeHourSlot(slot.key)}
                              >
                                Quitar
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
              <div className="flex justify-end gap-2 border-t border-slate-100 p-4">
                <button type="button" className="rounded-lg border px-3 py-2 text-sm" onClick={closeHoursRoom}>Cancelar</button>
                <button type="button" className={buttonClass} disabled={busy} onClick={() => void saveHoursRoom()}>
                  {busy ? "Guardando…" : "Guardar horarios"}
                </button>
              </div>
            </div>
          </div>
        )}
      </section>}

      {tab === "activities" && <section className="space-y-4">
        <form onSubmit={(e) => void createActivitySubmit(e)} className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-2">
          <Field label="Nombre" value={value("activityName")} onChange={(e) => setValue("activityName", e.target.value)} required />
          <Field label="Nivel" value={value("activityLevel")} onChange={(e) => setValue("activityLevel", e.target.value)} placeholder="inicial" />
          <Field label="Duración (minutos)" type="number" min="1" value={value("activityDuration")} onChange={(e) => setValue("activityDuration", e.target.value)} required />
          <RoomPickers selected={createRoomIds} onChange={setCreateRoomIds} />
          <div className="sm:col-span-2"><button type="submit" className={buttonClass} disabled={busy}>{busy ? "Guardando…" : "Guardar"}</button></div>
        </form>
        {list("activities").length === 0 ? (
          <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">No hay actividades.</p>
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {list("activities").map((activity) => (
              <li key={activity.id} className="flex flex-col gap-3 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="font-medium text-slate-900">{asText(activity.name)}{activity.active === false ? " · inactiva" : ""}</div>
                  <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
                    <span>nivel: {asText(activity.level)}</span>
                    <span>duración: {asText(activity.default_duration_minutes)} min</span>
                    <span>salones: {activityRoomLabels(activity)}</span>
                  </div>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button type="button" className="rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-700" onClick={() => openEditActivity(activity)}>Editar</button>
                  {activity.active !== false && (
                    <button type="button" className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50" onClick={() => void softDeleteActivity(activity)}>Eliminar</button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
        {editActivity && (
          <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center" role="dialog" aria-modal="true" aria-label="Editar actividad">
            <div className="max-h-[90dvh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-4 shadow-lg">
              <h3 className="text-lg font-semibold text-slate-900">Editar actividad</h3>
              {modalError && (
                <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
                  {modalError}
                </p>
              )}
              <div className="mt-3 grid gap-3">
                <Field label="Nombre" value={editActivityDraft.name} onChange={(e) => { setModalError(null); setEditActivityDraft((d) => ({ ...d, name: e.target.value })); }} />
                <Field label="Nivel" value={editActivityDraft.level} onChange={(e) => { setModalError(null); setEditActivityDraft((d) => ({ ...d, level: e.target.value })); }} />
                <Field label="Duración (minutos)" type="number" min="1" value={editActivityDraft.duration} onChange={(e) => { setModalError(null); setEditActivityDraft((d) => ({ ...d, duration: e.target.value })); }} />
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={editActivityDraft.active} onChange={(e) => { setModalError(null); setEditActivityDraft((d) => ({ ...d, active: e.target.checked })); }} /> Activa</label>
                <RoomPickers
                  selected={editActivityDraft.room_ids}
                  onChange={(next) => { setModalError(null); setEditActivityDraft((d) => ({ ...d, room_ids: next })); }}
                />
              </div>
              <div className="mt-4 flex justify-end gap-2">
                <button type="button" className="rounded-lg border px-3 py-2 text-sm" onClick={closeEditActivity}>Cancelar</button>
                <button type="button" className={buttonClass} disabled={busy} onClick={() => void saveEditActivity()}>{busy ? "Guardando…" : "Guardar"}</button>
              </div>
            </div>
          </div>
        )}
      </section>}

      {tab === "instructors" && <section className="space-y-4">
        <form
          onSubmit={(e) => void createInstructorSubmit(e)}
          autoComplete="off"
          className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-2"
        >
          <Field label="Nombre completo" name="studio-new-instructor-name" autoComplete="off" value={value("instructorName")} onChange={(e) => setValue("instructorName", e.target.value)} required />
          <Field label="Teléfono" name="studio-new-instructor-phone" autoComplete="off" value={value("instructorPhone")} onChange={(e) => setValue("instructorPhone", e.target.value)} />
          <div className="sm:col-span-2">
            <Field label="Email" type="email" name="studio-new-instructor-email" autoComplete="off" value={value("instructorEmail")} onChange={(e) => setValue("instructorEmail", e.target.value)} />
          </div>
          <div className="space-y-1 sm:col-span-2">
            <Field label="Contraseña de acceso (opcional)" type="password" name="studio-new-instructor-password" autoComplete="new-password" value={value("instructorPassword")} onChange={(e) => setValue("instructorPassword", e.target.value)} />
            <p className="text-xs text-slate-500">Si la completás, el mismo email será el de acceso a la app.</p>
          </div>
          <ActivityPickers selected={createInstructorActivityIds} onChange={setCreateInstructorActivityIds} />
          <div className="sm:col-span-2"><button type="submit" className={buttonClass} disabled={busy}>{busy ? "Guardando…" : "Guardar"}</button></div>
        </form>
        {list("instructors").length === 0 ? (
          <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">No hay instructores.</p>
        ) : (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {list("instructors").map((instructor) => (
              <li key={instructor.id} className="flex flex-col gap-3 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="font-medium text-slate-900">
                    {asText(instructor.full_name)}{instructor.active === false ? " · inactivo" : ""}
                  </div>
                  <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
                    <span>email: {asText(instructor.email)}</span>
                    <span>tel: {asText(instructor.phone)}</span>
                    <span>actividades: {instructorActivityLabels(instructor)}</span>
                  </div>
                </div>
                <div className="flex shrink-0 gap-2">
                  <button type="button" className="rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-700" onClick={() => openEditInstructor(instructor)}>Editar</button>
                  {instructor.active !== false && (
                    <button type="button" className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50" onClick={() => void softDeleteInstructor(instructor)}>Eliminar</button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
        {editInstructor && (
          <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center" role="dialog" aria-modal="true" aria-label="Editar instructor">
            <div className="flex max-h-[90dvh] w-full max-w-lg flex-col overflow-hidden rounded-xl bg-white shadow-lg">
              <div className="border-b border-slate-100 p-4">
                <h3 className="text-lg font-semibold text-slate-900">Editar instructor</h3>
                <p className="mt-1 text-xs text-slate-500">El email es único: contacto y acceso a la app.</p>
                {modalError && (
                  <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
                    {modalError}
                  </p>
                )}
              </div>
              <form
                autoComplete="off"
                onSubmit={(e) => { e.preventDefault(); void saveEditInstructor(); }}
                className="flex min-h-0 flex-1 flex-col"
              >
              <div className="min-h-0 flex-1 overflow-y-auto p-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="sm:col-span-2">
                    <Field label="Nombre completo" name="studio-edit-instructor-name" autoComplete="off" value={editInstructorDraft.full_name} onChange={(e) => { setModalError(null); setEditInstructorDraft((d) => ({ ...d, full_name: e.target.value })); }} />
                  </div>
                  <Field label="Email" type="email" name="studio-edit-instructor-email" autoComplete="off" value={editInstructorDraft.email} onChange={(e) => { setModalError(null); setEditInstructorDraft((d) => ({ ...d, email: e.target.value })); }} />
                  <Field label="Teléfono" name="studio-edit-instructor-phone" autoComplete="off" value={editInstructorDraft.phone} onChange={(e) => { setModalError(null); setEditInstructorDraft((d) => ({ ...d, phone: e.target.value })); }} />
                  <label className="flex items-center gap-2 text-sm sm:col-span-2">
                    <input type="checkbox" checked={editInstructorDraft.active} onChange={(e) => { setModalError(null); setEditInstructorDraft((d) => ({ ...d, active: e.target.checked })); }} />
                    Activo
                  </label>
                  <div className="sm:col-span-2">
                    <ActivityPickers
                      selected={editInstructorDraft.activity_ids}
                      onChange={(next) => { setModalError(null); setEditInstructorDraft((d) => ({ ...d, activity_ids: next })); }}
                    />
                  </div>
                  <div className="space-y-1 sm:col-span-2 border-t border-slate-100 pt-3">
                    <Field
                      label="Nueva contraseña (opcional)"
                      type="password"
                      name="studio-edit-instructor-password"
                      autoComplete="new-password"
                      value={editInstructorDraft.password}
                      onChange={(e) => {
                        setModalError(null);
                        setEditInstructorPasswordTouched(true);
                        setEditInstructorDraft((d) => ({ ...d, password: e.target.value }));
                      }}
                    />
                    <p className="text-xs text-slate-500">Dejala vacía para mantener la actual.</p>
                  </div>
                </div>
              </div>
              <div className="flex justify-end gap-2 border-t border-slate-100 p-4">
                <button type="button" className="rounded-lg border px-3 py-2 text-sm" onClick={closeEditInstructor}>Cancelar</button>
                <button type="submit" className={buttonClass} disabled={busy}>{busy ? "Guardando…" : "Guardar"}</button>
              </div>
              </form>
            </div>
          </div>
        )}
      </section>}
      {tab === "students" && <ProfileSection title="Alumno" endpoint="students" fields={["full_name", "email", "login_email", "password", "document_id", "emergency_contact", "emergency_phone", "medical_notes"]} items={list("students")} values={values} setValue={setValue} submit={submit} form={form} />}

      {tab === "series" && <section className="space-y-4">
        {form((e) => {
          e.preventDefault();
          const rawTime = value("seriesTime");
          const start_time = rawTime.length === 5 ? `${rawTime}:00` : rawTime;
          void submit("/api/v1/studio/series", {
            site_id: id("seriesSite"), room_id: id("seriesRoom"), activity_id: id("seriesActivity"),
            instructor_id: id("seriesInstructor"), weekday: Number(value("seriesWeekday")), start_time,
            duration_minutes: Number(value("seriesDuration")), capacity: Number(value("seriesCapacity")),
            level: value("seriesLevel") || "inicial",
          }, "Serie creada.");
        }, <>
          <Select
            label="Sede"
            field="seriesSite"
            items={selects.site}
            onChangeExtra={(nextSite) => {
              const activity = list("activities").find((item) => item.id === value("seriesActivity"));
              const linked = new Set(
                Array.isArray(activity?.room_ids) ? (activity.room_ids as string[]).map(String) : [],
              );
              const currentRoom = list("roomsAll").find((room) => room.id === value("seriesRoom"));
              if (!currentRoom) return;
              if (String(currentRoom.site_id) !== nextSite) {
                setValue("seriesRoom", "");
                return;
              }
              if (value("seriesActivity") && !linked.has(currentRoom.id)) setValue("seriesRoom", "");
            }}
          />
          <Select
            label="Actividad"
            field="seriesActivity"
            items={selects.activity}
            onChangeExtra={(nextActivityId) => {
              const activity = list("activities").find((item) => item.id === nextActivityId);
              const linked = new Set(
                Array.isArray(activity?.room_ids) ? (activity.room_ids as string[]).map(String) : [],
              );
              const siteId = value("seriesSite");
              const allowed = new Set(
                activeRooms
                  .filter((room) => {
                    if (siteId && String(room.site_id) !== siteId) return false;
                    if (nextActivityId && !linked.has(room.id)) return false;
                    return true;
                  })
                  .map((room) => room.id),
              );
              if (value("seriesRoom") && !allowed.has(value("seriesRoom"))) setValue("seriesRoom", "");
            }}
          />
          <Select
            label="Salón"
            field="seriesRoom"
            items={roomsForSeries()}
            required={Boolean(value("seriesSite") && value("seriesActivity"))}
          />
          {value("seriesSite") && value("seriesActivity") && roomsForSeries().length === 0 && (
            <p className="sm:col-span-2 text-sm text-amber-800">
              No hay salones compatibles (sede ∩ salones de la actividad). Asigná salones en <strong>Actividades</strong> o elegí otra combinación.
            </p>
          )}
          <Select label="Instructor" field="seriesInstructor" items={selects.instructor} />
          <Field label="Día (0 domingo · 6 sábado)" type="number" min="0" max="6" value={value("seriesWeekday")} onChange={(e) => setValue("seriesWeekday", e.target.value)} required />
          <Field label="Hora" type="time" step="1" value={value("seriesTime")} onChange={(e) => setValue("seriesTime", e.target.value)} required />
          <Field label="Duración (minutos)" type="number" min="1" value={value("seriesDuration")} onChange={(e) => setValue("seriesDuration", e.target.value)} required />
          <Field label="Capacidad" type="number" min="1" value={value("seriesCapacity")} onChange={(e) => setValue("seriesCapacity", e.target.value)} required />
          <Field label="Nivel" value={value("seriesLevel")} onChange={(e) => setValue("seriesLevel", e.target.value)} placeholder="inicial" />
        </>)}
        <List items={list("series")} fields={["weekday", "start_time", "duration_minutes", "capacity", "level", "active"]} />
        {form((e) => {
          e.preventDefault();
          void submit("/api/v1/studio/fixed-enrollments", {
            student_id: id("fixedStudent"), series_id: id("fixedSeries"), pack_id: id("fixedPack"),
          }, "Inscripción fija creada.", "series");
        }, <><Select label="Alumno (inscripción fija)" field="fixedStudent" items={selects.student} /><Select label="Serie" field="fixedSeries" items={list("series")} /><Select label="Paquete" field="fixedPack" items={selects.pack} /></>)}
      </section>}

      {tab === "sessions" && <section className="space-y-4">
        <div className="flex flex-col gap-2 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:flex-row sm:items-end"><Field label="Semanas a expandir" type="number" min="1" max="52" value={value("weeksAhead") || "4"} onChange={(e) => setValue("weeksAhead", e.target.value)} /><button type="button" className={buttonClass} disabled={busy} onClick={() => void submit(`/api/v1/studio/expand-sessions?weeks_ahead=${encodeURIComponent(value("weeksAhead") || "4")}`, undefined, "Sesiones expandidas.", "sessions")}>Expandir sesiones</button></div>
        <List items={list("sessions")} fields={["session_date", "start_time", "status", "capacity", "instructor_id"]} />
        {list("sessions").map((session) => <button key={session.id} type="button" className="mr-2 rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-700 hover:bg-red-50" onClick={() => { if (window.confirm("¿Cancelar esta sesión y sus reservas?")) void submit(`/api/v1/studio/sessions/${session.id}/mass-cancel`, {}, "Sesión cancelada.", "sessions"); }}>Cancelar {asText(session.session_date)} {asText(session.start_time)}</button>)}
      </section>}

      {tab === "holidays" && <section className="space-y-4">
        {form((e) => { e.preventDefault(); void submit("/api/v1/studio/holidays", { holiday_date: value("holidayDate"), name: value("holidayName"), site_id: id("holidaySite") || null }, "Feriado creado."); }, <><Field label="Fecha" type="date" value={value("holidayDate")} onChange={(e) => setValue("holidayDate", e.target.value)} required /><Field label="Nombre" value={value("holidayName")} onChange={(e) => setValue("holidayName", e.target.value)} required /><Select label="Sede (opcional)" field="holidaySite" items={selects.site} required={false} /></>)}
        <List items={list("holidays")} fields={["holiday_date", "name", "site_id"]} />
      </section>}

      {tab === "products" && <section className="space-y-4">
        {form((e) => { e.preventDefault(); void submit("/api/v1/studio/pack-products", { name: value("productName"), class_count: Number(value("productClasses")), validity_days: Number(value("productValidity")), price: value("productPrice") ? Number(value("productPrice")) : null, is_trial: value("productTrial") === "on" }, "Producto creado."); }, <><Field label="Nombre" value={value("productName")} onChange={(e) => setValue("productName", e.target.value)} required /><Field label="Cantidad de clases" type="number" min="1" value={value("productClasses")} onChange={(e) => setValue("productClasses", e.target.value)} required /><Field label="Vigencia (días)" type="number" min="1" value={value("productValidity")} onChange={(e) => setValue("productValidity", e.target.value)} required /><Field label="Precio (opcional)" type="number" min="0" step="0.01" value={value("productPrice")} onChange={(e) => setValue("productPrice", e.target.value)} /><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={value("productTrial") === "on"} onChange={(e) => setValue("productTrial", e.target.checked ? "on" : "")} /> Producto de prueba</label></>)}
        <List items={list("products")} fields={["name", "class_count", "validity_days", "price", "is_trial", "active"]} />
      </section>}

      {tab === "packs" && <section className="space-y-4">
        {form((e) => { e.preventDefault(); void submit("/api/v1/studio/student-packs", { student_id: id("assignStudent"), product_id: id("assignProduct"), starts_on: value("packStart"), scope: value("packScope") || "all_sedes", site_id: value("packScope") === "one_sede" ? id("packSite") : null, payment_method: value("paymentMethod") || "efectivo", payment_status: value("paymentStatus") || "pagado" }, "Paquete asignado.", "packs"); }, <><Select label="Alumno" field="assignStudent" items={selects.student} /><Select label="Producto" field="assignProduct" items={selects.product} /><Field label="Inicio" type="date" value={value("packStart")} onChange={(e) => setValue("packStart", e.target.value)} required /><label className="space-y-1 text-sm"><span>Alcance</span><select className={inputClass} value={value("packScope") || "all_sedes"} onChange={(e) => setValue("packScope", e.target.value)}><option value="all_sedes">Todas las sedes</option><option value="one_sede">Una sede</option></select></label>{value("packScope") === "one_sede" && <Select label="Sede" field="packSite" items={selects.site} />}<Field label="Medio de pago" value={value("paymentMethod")} onChange={(e) => setValue("paymentMethod", e.target.value)} placeholder="efectivo" /><Field label="Estado de pago" value={value("paymentStatus")} onChange={(e) => setValue("paymentStatus", e.target.value)} placeholder="pagado" /></>)}
        <div className="flex gap-2"><select className={inputClass} value={value("packStudent")} onChange={(e) => setValue("packStudent", e.target.value)}><option value="">Todos los alumnos</option>{selects.student.map((student) => <option key={student.id} value={student.id}>{asText(student.full_name)}</option>)}</select><button type="button" className="rounded-lg border px-3 text-sm" onClick={() => void loadTab()}>Buscar</button></div>
        <List items={list("packs")} fields={["student_id", "product_id", "remaining_credits", "starts_on", "expires_on", "scope"]} />
        {form((e) => { e.preventDefault(); void submit("/api/v1/studio/transfer-credits", { source_pack_id: id("sourcePack"), target_pack_id: id("targetPack"), credits: Number(value("transferCredits")) }, "Créditos transferidos.", "packs"); }, <><Select label="Paquete origen" field="sourcePack" items={selects.pack} /><Select label="Paquete destino" field="targetPack" items={selects.pack} /><Field label="Créditos" type="number" min="1" value={value("transferCredits")} onChange={(e) => setValue("transferCredits", e.target.value)} required /></>)}
      </section>}

      {tab === "audit" && <List items={list("audit")} fields={["action", "entity_type", "entity_id", "created_at", "actor_user_id"]} empty="No hay eventos de auditoría." />}
    </div>
  );
}

function ProfileSection({ title, endpoint, fields, items, values, setValue, submit, form }: {
  title: string; endpoint: "students"; fields: string[]; items: Item[];
  values: Record<string, string>; setValue: (key: string, value: string) => void;
  submit: (path: string, body: unknown, success: string) => Promise<void>;
  form: (onSubmit: (e: FormEvent) => void, children: React.ReactNode) => React.ReactNode;
}) {
  const prefix = endpoint;
  const labels: Record<string, string> = { full_name: "Nombre completo", email: "Email de contacto", login_email: "Email de acceso", password: "Contraseña (mín. 8)", document_id: "Documento", emergency_contact: "Contacto de emergencia", emergency_phone: "Teléfono de emergencia", medical_notes: "Notas médicas" };
  return <section className="space-y-4">
    {form((e) => {
      e.preventDefault();
      const body = Object.fromEntries(fields.map((field) => [field, values[`${prefix}-${field}`] || null]));
      if (!body.login_email) delete body.login_email;
      if (!body.password) delete body.password;
      void submit(`/api/v1/studio/${endpoint}`, body, `${title} creado.`);
    }, <>{fields.map((field) => <Field key={field} label={labels[field]} type={field === "password" ? "password" : "text"} value={values[`${prefix}-${field}`] ?? ""} onChange={(e) => setValue(`${prefix}-${field}`, e.target.value)} required={field === "full_name"} />)}</>)}
    <List items={items} fields={["full_name", "email", "document_id", "active"]} />
  </section>;
}
