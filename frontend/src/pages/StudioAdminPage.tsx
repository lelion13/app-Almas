import { useEffect, useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { ApiError, apiFetch } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";

type Item = Record<string, unknown> & { id: string };
type Tab =
  | "sites" | "rooms" | "activities" | "instructors" | "students" | "series"
  | "sessions" | "holidays" | "products" | "packs" | "audit";

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
  const [busy, setBusy] = useState(false);

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
  const roomsForSite = (siteId: string) =>
    list("roomsAll").filter((room) => !siteId || String(room.site_id) === siteId);
  const activeSites = list("sites").filter((site) => site.active !== false);
  const selects = {
    site: activeSites, room: list("roomsAll"), activity: list("activities"),
    instructor: list("instructors"), student: list("students"), product: list("products"), pack: list("packs"),
  };
  const allSites = list("sites");

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
        {form((e) => { e.preventDefault(); void submit("/api/v1/studio/rooms", { site_id: id("newRoomSite"), name: value("roomName"), capacity: Number(value("roomCapacity")) }, "Salón creado."); }, <><Select label="Sede" field="newRoomSite" items={selects.site} /><Field label="Nombre" value={value("roomName")} onChange={(e) => setValue("roomName", e.target.value)} required /><Field label="Capacidad" type="number" min="1" value={value("roomCapacity")} onChange={(e) => setValue("roomCapacity", e.target.value)} required /></>)}
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
              <li key={room.id} className="px-4 py-3 text-sm">
                <div className="font-medium text-slate-900">{asText(room.name)}</div>
                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
                  <span>sede: {siteName(room.site_id)}</span>
                  <span>capacidad: {asText(room.capacity)}</span>
                  <span>activo: {asText(room.active)}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>}

      {tab === "activities" && <section className="space-y-4">
        {form((e) => { e.preventDefault(); void submit("/api/v1/studio/activities", { name: value("activityName"), level: value("activityLevel") || "inicial", default_duration_minutes: Number(value("activityDuration") || 60) }, "Actividad creada."); }, <><Field label="Nombre" value={value("activityName")} onChange={(e) => setValue("activityName", e.target.value)} required /><Field label="Nivel" value={value("activityLevel")} onChange={(e) => setValue("activityLevel", e.target.value)} placeholder="inicial" /><Field label="Duración (minutos)" type="number" min="1" value={value("activityDuration")} onChange={(e) => setValue("activityDuration", e.target.value)} required /></>)}
        <List items={list("activities")} fields={["name", "level", "default_duration_minutes", "active"]} />
      </section>}

      {tab === "instructors" && <ProfileSection title="Instructor" endpoint="instructors" fields={["full_name", "email", "login_email", "password"]} items={list("instructors")} values={values} setValue={setValue} submit={submit} form={form} />}
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
            onChangeExtra={(next) => {
              const currentRoom = list("roomsAll").find((room) => room.id === value("seriesRoom"));
              if (currentRoom && String(currentRoom.site_id) !== next) setValue("seriesRoom", "");
            }}
          />
          <Select
            label="Salón"
            field="seriesRoom"
            items={roomsForSite(value("seriesSite"))}
            required={Boolean(value("seriesSite"))}
          />
          {value("seriesSite") && roomsForSite(value("seriesSite")).length === 0 && (
            <p className="sm:col-span-2 text-sm text-amber-800">
              No hay salones para esta sede. Creá uno en la pestaña <strong>Salones</strong> y volvé acá.
            </p>
          )}
          <Select label="Actividad" field="seriesActivity" items={selects.activity} />
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
  title: string; endpoint: "instructors" | "students"; fields: string[]; items: Item[];
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
