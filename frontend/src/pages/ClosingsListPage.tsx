import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch, ApiError } from "@/services/api";

type Closing = {
  id: string;
  year: number;
  month: number;
  status: string;
  notes: string | null;
  created_at: string;
};

const months = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];

export default function ClosingsListPage() {
  const [items, setItems] = useState<Closing[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [busy, setBusy] = useState(false);

  async function load() {
    setErr(null);
    try {
      const data = await apiFetch<Closing[]>("/api/v1/closings");
      setItems(data);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Error al cargar cierres.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function createClosing(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await apiFetch<Closing>("/api/v1/closings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ year, month }),
      });
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "No se pudo crear el cierre.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Cierres mensuales</h1>
        <p className="text-sm text-slate-600 mt-1">
          Importá pagos desde SigueFit y cargá gastos manuales por mes.
        </p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-medium text-slate-800 mb-3">Nuevo cierre</h2>
        <form onSubmit={createClosing} className="flex flex-col sm:flex-row gap-3 sm:items-end">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Año</label>
            <input
              type="number"
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm w-full sm:w-28"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              min={2000}
              max={2100}
            />
          </div>
          <div className="flex-1">
            <label className="block text-xs text-slate-500 mb-1">Mes</label>
            <select
              className="rounded-lg border border-slate-200 px-3 py-2 text-sm w-full"
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
            >
              {months.map((m, i) => (
                <option key={m} value={i + 1}>
                  {m}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-brand-700 text-white px-4 py-2 text-sm font-medium hover:bg-brand-900 disabled:opacity-50"
          >
            Crear
          </button>
        </form>
        {err && <p className="mt-2 text-sm text-red-600">{err}</p>}
      </section>

      <section>
        <h2 className="text-sm font-medium text-slate-800 mb-3">Listado</h2>
        <ul className="space-y-2">
          {items.length === 0 && <li className="text-sm text-slate-500">No hay cierres aún.</li>}
          {items.map((c) => (
            <li key={c.id}>
              <Link
                to={`/closings/${c.id}`}
                className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 rounded-xl border border-slate-200 bg-white p-4 shadow-sm hover:border-brand-300 transition-colors"
              >
                <span className="font-medium text-slate-900">
                  {months[c.month - 1]} {c.year}
                </span>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full w-fit ${
                    c.status === "finalized"
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-amber-100 text-amber-900"
                  }`}
                >
                  {c.status === "finalized" ? "Finalizado" : "Borrador"}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
