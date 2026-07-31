import { useEffect, useMemo, useState } from "react";
import { Navigate, useSearchParams } from "react-router-dom";
import { apiFetch, ApiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";

type Tab = "cuentas" | "movimientos";

type MpAccount = {
  id: string;
  name: string;
  external_user_id: string | null;
  token_last4: string;
  token_expires_at: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

type MovementRow = {
  source_id: string;
  transaction_date: string | null;
  transaction_type: string;
  transaction_type_label: string;
  bucket: "ingreso" | "egreso" | "otro";
  amount: string;
  currency: string;
  description: string | null;
  external_reference: string | null;
  fee_amount: string | null;
};

function daysBetween(from: string, to: string): number {
  const a = new Date(from);
  const b = new Date(to);
  return (b.getTime() - a.getTime()) / (1000 * 60 * 60 * 24);
}

const BUCKET_LABEL: Record<MovementRow["bucket"], string> = {
  ingreso: "Ingreso",
  egreso: "Egreso",
  otro: "Otro",
};

export default function ConciliacionPage() {
  const { me } = useAuth();
  const [params, setParams] = useSearchParams();
  const [tab, setTab] = useState<Tab>("cuentas");
  const [accounts, setAccounts] = useState<MpAccount[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadingMovements, setLoadingMovements] = useState(false);

  const [accountId, setAccountId] = useState("");
  const [fromDt, setFromDt] = useState("");
  const [toDt, setToDt] = useState("");
  const [movements, setMovements] = useState<MovementRow[]>([]);
  const [bucketFilter, setBucketFilter] = useState<"all" | "ingreso" | "egreso">("all");
  const [typeFilter, setTypeFilter] = useState("all");
  const [currencyFilter, setCurrencyFilter] = useState("all");
  const [textFilter, setTextFilter] = useState("");

  async function loadAccounts() {
    try {
      const data = await apiFetch<MpAccount[]>("/api/v1/mp/accounts");
      setAccounts(data);
      if (!accountId && data.length > 0) {
        const firstActive = data.find((a) => a.active) ?? data[0];
        setAccountId(firstActive.id);
      }
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "No se pudieron cargar las cuentas.");
    }
  }

  useEffect(() => {
    void loadAccounts();
  }, []);

  useEffect(() => {
    const oauth = params.get("oauth");
    if (!oauth) return;
    if (oauth === "ok") {
      setMsg("Cuenta de Mercado Pago conectada.");
      setTab("cuentas");
      void loadAccounts();
    } else {
      setErr(decodeURIComponent(params.get("detail") || "") || "No se pudo completar OAuth con Mercado Pago.");
    }
    params.delete("oauth");
    params.delete("detail");
    setParams(params, { replace: true });
  }, [params, setParams]);

  if (me?.role !== "admin") {
    return <Navigate to="/" replace />;
  }

  async function connectAccount(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    setBusy(true);
    try {
      const res = await apiFetch<{ authorization_url: string }>("/api/v1/mp/oauth/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim() || null }),
      });
      window.location.href = res.authorization_url;
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "No se pudo iniciar OAuth.");
      setBusy(false);
    }
  }

  async function patchAccount(id: string, body: { name?: string; active?: boolean }) {
    setErr(null);
    try {
      await apiFetch(`/api/v1/mp/accounts/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      await loadAccounts();
      setMsg("Cuenta actualizada.");
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "No se pudo actualizar la cuenta.");
    }
  }

  async function searchMovements(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setMsg(null);
    if (!accountId) {
      setErr("Seleccioná una cuenta.");
      return;
    }
    if (!fromDt || !toDt) {
      setErr("Indicá fecha desde y hasta.");
      return;
    }
    if (daysBetween(fromDt, toDt) > 60) {
      setErr("El rango no puede superar 60 días.");
      return;
    }
    setLoadingMovements(true);
    setBusy(true);
    try {
      const res = await apiFetch<{ items: MovementRow[] }>(
        `/api/v1/mp/accounts/${accountId}/movements/search`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            from_datetime: new Date(fromDt).toISOString(),
            to_datetime: new Date(toDt).toISOString(),
          }),
        }
      );
      setMovements(res.items);
      setMsg(`${res.items.length} movimientos encontrados.`);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "No se pudieron consultar los movimientos.");
      setMovements([]);
    } finally {
      setBusy(false);
      setLoadingMovements(false);
    }
  }

  const filtered = useMemo(() => {
    return movements.filter((m) => {
      if (bucketFilter !== "all" && m.bucket !== bucketFilter) return false;
      if (typeFilter !== "all" && m.transaction_type !== typeFilter) return false;
      if (currencyFilter !== "all" && m.currency !== currencyFilter) return false;
      if (textFilter.trim()) {
        const q = textFilter.trim().toLowerCase();
        const blob = `${m.source_id} ${m.description ?? ""} ${m.external_reference ?? ""} ${m.transaction_type_label}`.toLowerCase();
        if (!blob.includes(q)) return false;
      }
      return true;
    });
  }, [movements, bucketFilter, typeFilter, currencyFilter, textFilter]);

  const types = useMemo(() => {
    const map = new Map<string, string>();
    for (const m of movements) {
      if (m.transaction_type) map.set(m.transaction_type, m.transaction_type_label);
    }
    return Array.from(map.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  }, [movements]);

  const currencies = useMemo(
    () => Array.from(new Set(movements.map((m) => m.currency).filter(Boolean))).sort(),
    [movements]
  );

  const tabCls = (t: Tab) =>
    `rounded-lg px-3 py-2 text-sm font-medium ${
      tab === t ? "bg-brand-100 text-brand-900" : "text-slate-600 hover:bg-slate-100"
    }`;

  const bucketBtn = (value: typeof bucketFilter, label: string) => (
    <button
      type="button"
      key={value}
      onClick={() => setBucketFilter(value)}
      className={`rounded-lg px-3 py-1.5 text-sm ${
        bucketFilter === value
          ? "bg-brand-700 text-white"
          : "border border-slate-200 text-slate-700 hover:bg-slate-50"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Conciliación</h1>
        <p className="mt-1 text-sm text-slate-600">
          Conectá cuentas de Mercado Pago y consultá cobros y devoluciones (rápido, sin guardar ni vincular a
          cierres). Los retiros a banco no entran en esta consulta.
        </p>
      </div>

      <div className="flex gap-2 flex-wrap">
        <button type="button" className={tabCls("cuentas")} onClick={() => setTab("cuentas")}>
          Cuentas Mercado Pago
        </button>
        <button type="button" className={tabCls("movimientos")} onClick={() => setTab("movimientos")}>
          Movimientos
        </button>
      </div>

      {err && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{err}</div>
      )}
      {msg && !loadingMovements && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {msg}
        </div>
      )}

      {tab === "cuentas" && (
        <div className="space-y-6">
          <form onSubmit={connectAccount} className="flex flex-col sm:flex-row gap-2 max-w-xl">
            <input
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="Nombre interno (opcional)"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800 disabled:opacity-60"
            >
              {busy ? "Redirigiendo…" : "Conectar cuenta"}
            </button>
          </form>

          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {accounts.length === 0 && (
              <li className="px-4 py-6 text-sm text-slate-500">No hay cuentas conectadas.</li>
            )}
            {accounts.map((a) => (
              <li key={a.id} className="px-4 py-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <div className="font-medium text-slate-900">{a.name}</div>
                  <div className="text-xs text-slate-500">
                    {a.active ? "Activa" : "Desactivada"}
                    {a.external_user_id ? ` · MP user ${a.external_user_id}` : ""}
                    {a.token_last4 ? ` · token …${a.token_last4}` : ""}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs hover:bg-slate-50"
                    onClick={() => {
                      const name = window.prompt("Nombre interno", a.name);
                      if (name && name.trim() && name.trim() !== a.name) {
                        void patchAccount(a.id, { name: name.trim() });
                      }
                    }}
                  >
                    Renombrar
                  </button>
                  <button
                    type="button"
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs hover:bg-slate-50"
                    onClick={() => void patchAccount(a.id, { active: !a.active })}
                  >
                    {a.active ? "Desactivar" : "Activar"}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {tab === "movimientos" && (
        <div className="relative space-y-4">
          {loadingMovements && (
            <div
              className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 rounded-xl bg-white/85 backdrop-blur-[2px] min-h-[280px]"
              role="status"
              aria-live="polite"
            >
              <div
                className="h-10 w-10 rounded-full border-2 border-brand-200 border-t-brand-700 animate-spin"
                aria-hidden
              />
              <div className="text-center px-4">
                <p className="text-sm font-medium text-slate-900">Consultando movimientos…</p>
                <p className="mt-1 text-xs text-slate-500 max-w-sm">
                  Buscando cobros y devoluciones en Mercado Pago.
                </p>
              </div>
            </div>
          )}

          <form onSubmit={searchMovements} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 max-w-4xl">
            <label className="text-sm space-y-1">
              <span className="text-slate-600">Cuenta</span>
              <select
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
                disabled={loadingMovements}
              >
                <option value="">Seleccionar…</option>
                {accounts
                  .filter((a) => a.active)
                  .map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.name}
                    </option>
                  ))}
              </select>
            </label>
            <label className="text-sm space-y-1">
              <span className="text-slate-600">Desde</span>
              <input
                type="datetime-local"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={fromDt}
                onChange={(e) => setFromDt(e.target.value)}
                disabled={loadingMovements}
              />
            </label>
            <label className="text-sm space-y-1">
              <span className="text-slate-600">Hasta</span>
              <input
                type="datetime-local"
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
                value={toDt}
                onChange={(e) => setToDt(e.target.value)}
                disabled={loadingMovements}
              />
            </label>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={busy || loadingMovements}
                className="w-full rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-800 disabled:opacity-60"
              >
                {loadingMovements ? "Generando…" : "Consultar"}
              </button>
            </div>
          </form>

          <div className="flex flex-wrap gap-2 items-center">
            {bucketBtn("all", "Todos")}
            {bucketBtn("ingreso", "Ingresos")}
            {bucketBtn("egreso", "Egresos")}
          </div>

          <div className="flex flex-col sm:flex-row gap-2 max-w-4xl">
            <select
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              disabled={loadingMovements}
            >
              <option value="all">Todos los tipos</option>
              {types.map(([code, label]) => (
                <option key={code} value={code}>
                  {label}
                </option>
              ))}
            </select>
            <select
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
              value={currencyFilter}
              onChange={(e) => setCurrencyFilter(e.target.value)}
              disabled={loadingMovements}
            >
              <option value="all">Todas las monedas</option>
              {currencies.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <input
              className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
              placeholder="Filtrar texto (id, descripción, ref.)"
              value={textFilter}
              onChange={(e) => setTextFilter(e.target.value)}
              disabled={loadingMovements}
            />
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">Fecha</th>
                  <th className="px-3 py-2">Tipo</th>
                  <th className="px-3 py-2">Grupo</th>
                  <th className="px-3 py-2">Monto</th>
                  <th className="px-3 py-2">Moneda</th>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Ref. externa</th>
                  <th className="px-3 py-2">Descripción</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-3 py-6 text-slate-500">
                      {loadingMovements ? "Esperando reporte…" : "Sin resultados."}
                    </td>
                  </tr>
                ) : (
                  filtered.map((m, idx) => (
                    <tr key={`${m.source_id}-${m.transaction_type}-${idx}`} className="border-t border-slate-100">
                      <td className="px-3 py-2 whitespace-nowrap">
                        {m.transaction_date ? new Date(m.transaction_date).toLocaleString() : "—"}
                      </td>
                      <td className="px-3 py-2">{m.transaction_type_label}</td>
                      <td className="px-3 py-2">{BUCKET_LABEL[m.bucket]}</td>
                      <td className="px-3 py-2">{m.amount}</td>
                      <td className="px-3 py-2">{m.currency || "—"}</td>
                      <td className="px-3 py-2 font-mono text-xs">{m.source_id || "—"}</td>
                      <td className="px-3 py-2">{m.external_reference ?? "—"}</td>
                      <td className="px-3 py-2">{m.description ?? "—"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
