import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { apiFetch, ApiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";

type Teacher = { id: string; full_name: string; active: boolean; created_at: string };

export default function TeachersPage() {
  const { me } = useAuth();
  const [items, setItems] = useState<Teacher[]>([]);
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    try {
      const data = await apiFetch<Teacher[]>("/api/v1/teachers?include_inactive=true");
      setItems(data);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Error");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (me?.role !== "admin") {
    return <Navigate to="/" replace />;
  }

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      await apiFetch("/api/v1/teachers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ full_name: name, active: true }),
      });
      setName("");
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "No se pudo crear.");
    }
  }

  return (
    <div className="space-y-6 max-w-lg">
      <h1 className="text-2xl font-semibold text-slate-900">Profesoras</h1>
      <form onSubmit={add} className="flex gap-2 flex-col sm:flex-row">
        <input
          className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm"
          placeholder="Nombre completo"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <button type="submit" className="rounded-lg bg-brand-700 text-white px-4 py-2 text-sm">
          Agregar
        </button>
      </form>
      {err && <p className="text-sm text-red-600">{err}</p>}
      <ul className="space-y-2">
        {items.map((t) => (
          <li
            key={t.id}
            className="flex justify-between items-center rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm"
          >
            <span>{t.full_name}</span>
            <span className={t.active ? "text-emerald-700 text-xs" : "text-slate-400 text-xs"}>
              {t.active ? "Activa" : "Inactiva"}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
