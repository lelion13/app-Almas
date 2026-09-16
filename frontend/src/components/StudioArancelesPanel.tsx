import { useEffect, useState, type FormEvent } from "react";
import { ApiError, apiFetch } from "@/services/api";

type Item = Record<string, unknown> & { id: string };

const inputClass = "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm";
const buttonClass = "rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800 disabled:opacity-60";

function asText(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

type Props = {
  activities: Item[];
};

export default function StudioArancelesPanel({ activities }: Props) {
  const [items, setItems] = useState<Item[]>([]);
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [classesPerWeek, setClassesPerWeek] = useState("1");
  const [activityIds, setActivityIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [edit, setEdit] = useState<Item | null>(null);
  const [editDraft, setEditDraft] = useState({ name: "", price: "", classes_per_week: "1", activity_ids: [] as string[], active: true });
  const [modalError, setModalError] = useState<string | null>(null);

  async function load() {
    try {
      const rows = await apiFetch<Item[]>("/api/v1/studio/aranceles");
      setItems(rows);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudieron cargar los aranceles.");
    }
  }

  useEffect(() => { void load(); }, []);

  function toggleActivity(id: string, selected: string[], setSelected: (v: string[]) => void) {
    setSelected(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  }

  async function createSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null); setNotice(null);
    try {
      await apiFetch("/api/v1/studio/aranceles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          price: Number(price),
          classes_per_week: Number(classesPerWeek),
          activity_ids: activityIds,
          active: true,
        }),
      });
      setName(""); setPrice(""); setClassesPerWeek("1"); setActivityIds([]);
      setNotice("Arancel creado.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar.");
    } finally {
      setBusy(false);
    }
  }

  function openEdit(item: Item) {
    setModalError(null);
    setEdit(item);
    setEditDraft({
      name: String(item.name ?? ""),
      price: String(item.price ?? ""),
      classes_per_week: String(item.classes_per_week ?? 1),
      activity_ids: Array.isArray(item.activity_ids) ? (item.activity_ids as string[]) : [],
      active: item.active !== false,
    });
  }

  async function saveEdit() {
    if (!edit) return;
    setBusy(true); setModalError(null);
    try {
      await apiFetch(`/api/v1/studio/aranceles/${edit.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: editDraft.name,
          price: Number(editDraft.price),
          classes_per_week: Number(editDraft.classes_per_week),
          activity_ids: editDraft.activity_ids,
          active: editDraft.active,
        }),
      });
      setEdit(null);
      setNotice("Arancel actualizado.");
      await load();
    } catch (err) {
      setModalError(err instanceof ApiError ? err.message : "No se pudo guardar.");
    } finally {
      setBusy(false);
    }
  }

  async function softDelete(item: Item) {
    if (!window.confirm(`¿Desactivar arancel “${asText(item.name)}”?`)) return;
    setBusy(true); setError(null);
    try {
      await apiFetch(`/api/v1/studio/aranceles/${item.id}`, { method: "DELETE" });
      setNotice("Arancel desactivado.");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo desactivar.");
    } finally {
      setBusy(false);
    }
  }

  const activeActivities = activities.filter((a) => a.active !== false);
  const activityName = (id: string) => asText(activities.find((a) => a.id === id)?.name ?? id);

  return (
    <section className="space-y-4">
      {error && <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">{error}</p>}
      {notice && <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{notice}</p>}

      <form onSubmit={(e) => void createSubmit(e)} className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-2">
        <label className="space-y-1 text-sm text-slate-700"><span>Nombre</span><input className={inputClass} value={name} onChange={(e) => setName(e.target.value)} required /></label>
        <label className="space-y-1 text-sm text-slate-700"><span>Valor</span><input className={inputClass} type="number" min="0" step="0.01" value={price} onChange={(e) => setPrice(e.target.value)} required /></label>
        <label className="space-y-1 text-sm text-slate-700"><span>Clases por semana</span><input className={inputClass} type="number" min="1" value={classesPerWeek} onChange={(e) => setClassesPerWeek(e.target.value)} required /></label>
        <div className="space-y-2 sm:col-span-2">
          <div className="text-sm font-medium text-slate-700">Actividades</div>
          <div className="flex flex-wrap gap-2">
            {activeActivities.map((a) => (
              <label key={a.id} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm">
                <input type="checkbox" checked={activityIds.includes(a.id)} onChange={() => toggleActivity(a.id, activityIds, setActivityIds)} />
                {asText(a.name)}
              </label>
            ))}
          </div>
          {!activeActivities.length && <p className="text-xs text-slate-500">Creá actividades primero.</p>}
        </div>
        <div className="sm:col-span-2"><button type="submit" className={buttonClass} disabled={busy || !activityIds.length}>{busy ? "Guardando…" : "Guardar arancel"}</button></div>
      </form>

      {items.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 px-4 py-6 text-sm text-slate-500">No hay aranceles.</p>
      ) : (
        <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
          {items.map((item) => (
            <li key={item.id} className="flex flex-col gap-3 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="font-medium text-slate-900">{asText(item.name)}{item.active === false ? " · inactivo" : ""}</div>
                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-xs text-slate-500">
                  <span>valor: {asText(item.price)}</span>
                  <span>clases/semana: {asText(item.classes_per_week)}</span>
                  <span>actividades: {(Array.isArray(item.activity_ids) ? item.activity_ids as string[] : []).map(activityName).join(", ") || "—"}</span>
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                <button type="button" className="rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-700" onClick={() => openEdit(item)}>Editar</button>
                {item.active !== false && (
                  <button type="button" className="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50" onClick={() => void softDelete(item)}>Eliminar</button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {edit && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-900/40 p-4 sm:items-center" role="dialog" aria-modal="true">
          <div className="w-full max-w-lg rounded-xl bg-white shadow-lg">
            <div className="border-b border-slate-100 p-4">
              <h3 className="text-lg font-semibold text-slate-900">Editar arancel</h3>
              {modalError && <p className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{modalError}</p>}
            </div>
            <div className="grid gap-3 p-4 sm:grid-cols-2">
              <label className="space-y-1 text-sm"><span>Nombre</span><input className={inputClass} value={editDraft.name} onChange={(e) => setEditDraft((d) => ({ ...d, name: e.target.value }))} /></label>
              <label className="space-y-1 text-sm"><span>Valor</span><input className={inputClass} type="number" min="0" step="0.01" value={editDraft.price} onChange={(e) => setEditDraft((d) => ({ ...d, price: e.target.value }))} /></label>
              <label className="space-y-1 text-sm"><span>Clases/semana</span><input className={inputClass} type="number" min="1" value={editDraft.classes_per_week} onChange={(e) => setEditDraft((d) => ({ ...d, classes_per_week: e.target.value }))} /></label>
              <label className="flex items-center gap-2 self-end pb-2 text-sm"><input type="checkbox" checked={editDraft.active} onChange={(e) => setEditDraft((d) => ({ ...d, active: e.target.checked }))} /> Activo</label>
              <div className="space-y-2 sm:col-span-2">
                <div className="text-sm font-medium">Actividades</div>
                <div className="flex flex-wrap gap-2">
                  {activeActivities.map((a) => (
                    <label key={a.id} className="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm">
                      <input
                        type="checkbox"
                        checked={editDraft.activity_ids.includes(a.id)}
                        onChange={() => toggleActivity(a.id, editDraft.activity_ids, (ids) => setEditDraft((d) => ({ ...d, activity_ids: ids })))}
                      />
                      {asText(a.name)}
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t border-slate-100 p-4">
              <button type="button" className="rounded-lg border px-3 py-2 text-sm" onClick={() => setEdit(null)}>Cancelar</button>
              <button type="button" className={buttonClass} disabled={busy || !editDraft.activity_ids.length} onClick={() => void saveEdit()}>{busy ? "Guardando…" : "Guardar"}</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
