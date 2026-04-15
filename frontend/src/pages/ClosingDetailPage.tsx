import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiFetch, ApiError } from "@/services/api";
import { useAuth } from "@/hooks/useAuth";
import CurrencyARS, { formatArs } from "@/components/CurrencyARS";

type Closing = {
  id: string;
  year: number;
  month: number;
  status: string;
  notes: string | null;
};

type GroupRow = { key: string; total_amount: string; line_count: number };
type Overview = {
  total_amount: string;
  positive_total: string;
  negative_total: string;
  distinct_clients: number;
};

type Expense = {
  id: string;
  expense_type: string;
  vendor_or_teacher_name: string | null;
  teacher_id: string | null;
  hours: string | null;
  hourly_rate: string | null;
  amount: string;
  expense_date: string;
  description: string | null;
};

type Teacher = { id: string; full_name: string; active: boolean };

type ImportBatch = {
  id: string;
  closing_id: string;
  original_filename: string;
  file_sha256: string;
  source_from: string | null;
  source_to: string | null;
  activity_filter: string | null;
  uploaded_at: string;
};

type YogaAttributionLine = {
  line_id: string;
  payment_date: string | null;
  client_name: string | null;
  payment_category: string;
  amount: string;
  rule_label: string;
  yoga_amount: string;
};

type YogaAttribution = {
  items: YogaAttributionLine[];
  total_yoga: string;
};

const months = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

/** Ingresos (SigueFit) y egresos (Excel gastos) por método; "Transferencia Lea" se acumula como "Transferencia Mercedes". */
const MERCEDES_BUCKET = "Transferencia Mercedes";
const LEA_METHOD = "Transferencia Lea";

function bucketPaymentMethodLabel(key: string): string {
  const t = key.trim();
  if (t === LEA_METHOD) return MERCEDES_BUCKET;
  return t || "—";
}

type MethodCashflowRow = {
  label: string;
  ingresos: number;
  egresos: number;
  saldo: number;
};

function buildMethodCashflowRows(incomeByMethod: GroupRow[], expenseByMethod: GroupRow[]): MethodCashflowRow[] {
  const acc = new Map<string, { ingresos: number; egresos: number }>();
  for (const r of incomeByMethod) {
    const label = bucketPaymentMethodLabel(r.key);
    const prev = acc.get(label) ?? { ingresos: 0, egresos: 0 };
    prev.ingresos += Number(r.total_amount);
    acc.set(label, prev);
  }
  for (const r of expenseByMethod) {
    const label = bucketPaymentMethodLabel(r.key);
    const prev = acc.get(label) ?? { ingresos: 0, egresos: 0 };
    prev.egresos += Number(r.total_amount);
    acc.set(label, prev);
  }
  const preferredOrder = ["Efectivo", "Transferencia Irene", MERCEDES_BUCKET, "Transferencia Raquel"];
  const labels = [...acc.keys()].sort((a, b) => {
    const ia = preferredOrder.indexOf(a);
    const ib = preferredOrder.indexOf(b);
    if (ia >= 0 && ib >= 0) return ia - ib;
    if (ia >= 0) return -1;
    if (ib >= 0) return 1;
    return a.localeCompare(b, "es");
  });
  return labels.map((label) => {
    const v = acc.get(label)!;
    return {
      label,
      ingresos: v.ingresos,
      egresos: v.egresos,
      saldo: v.ingresos - v.egresos,
    };
  });
}

const IRENE_METHOD = "Transferencia Irene";

function saldoByMethod(rows: MethodCashflowRow[], label: string): number {
  const r = rows.find((x) => x.label === label);
  return r ? r.saldo : 0;
}

/** Reparto 50/50 del saldo total; pool = saldo no atribuible a transfer Irene ni Mercedes (efectivo, Raquel, etc.). */
function computePartnerProfitSplit(rows: MethodCashflowRow[], totalSaldo: number) {
  const T = totalSaldo;
  const H = T / 2;
  const tI = saldoByMethod(rows, IRENE_METHOD);
  const tM = saldoByMethod(rows, MERCEDES_BUCKET);
  const pool = T - tI - tM;
  const needI = Math.max(0, H - tI);
  const needM = Math.max(0, H - tM);
  let remaining = pool;
  let giveI = 0;
  let giveM = 0;
  if (tI <= tM) {
    giveI = Math.min(remaining, needI);
    remaining -= giveI;
    giveM = Math.min(remaining, needM);
  } else {
    giveM = Math.min(remaining, needM);
    remaining -= giveM;
    giveI = Math.min(remaining, needI);
  }
  const poolRestante = pool - giveI - giveM;
  return {
    totalSaldo: T,
    metaCadaUna: H,
    pool,
    irene: {
      transferencia: tI,
      desdePool: giveI,
      meta: H,
      total: tI + giveI,
    },
    mercedes: {
      transferencia: tM,
      desdePool: giveM,
      meta: H,
      total: tM + giveM,
    },
    poolRestante,
  };
}

export default function ClosingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { me } = useAuth();
  const [closing, setClosing] = useState<Closing | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [cats, setCats] = useState<GroupRow[]>([]);
  const [methods, setMethods] = useState<GroupRow[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [teachers, setTeachers] = useState<Teacher[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [expenseType, setExpenseType] = useState<"service" | "teacher_hours">("service");
  const [vendor, setVendor] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [hours, setHours] = useState("");
  const [hourlyRate, setHourlyRate] = useState("");
  const [amount, setAmount] = useState("");
  const [expenseDate, setExpenseDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [description, setDescription] = useState("");
  const [importBatches, setImportBatches] = useState<ImportBatch[]>([]);
  const [expenseImportBatches, setExpenseImportBatches] = useState<ImportBatch[]>([]);
  const [expenseMethods, setExpenseMethods] = useState<GroupRow[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deletingExpenseId, setDeletingExpenseId] = useState<string | null>(null);
  const [uploadIncomeBusy, setUploadIncomeBusy] = useState(false);
  const [uploadExpenseBusy, setUploadExpenseBusy] = useState(false);
  const [yogaAttribution, setYogaAttribution] = useState<YogaAttribution | null>(null);

  const methodCashflowRows = useMemo(
    () => buildMethodCashflowRows(methods, expenseMethods),
    [methods, expenseMethods],
  );

  const methodCashflowTotals = useMemo(() => {
    let ing = 0;
    let egr = 0;
    for (const r of methodCashflowRows) {
      ing += r.ingresos;
      egr += r.egresos;
    }
    return { ingresos: ing, egresos: egr, saldo: ing - egr };
  }, [methodCashflowRows]);

  const partnerProfitSplit = useMemo(
    () => computePartnerProfitSplit(methodCashflowRows, methodCashflowTotals.saldo),
    [methodCashflowRows, methodCashflowTotals.saldo],
  );

  const load = useCallback(async () => {
    if (!id) return;
    setErr(null);
    try {
      const [c, o, cc, mm, em, ya, ex, tt, imp, eimp] = await Promise.all([
        apiFetch<Closing>(`/api/v1/closings/${id}`),
        apiFetch<Overview>(`/api/v1/closings/${id}/summary/overview`),
        apiFetch<GroupRow[]>(`/api/v1/closings/${id}/summary/payment-categories`),
        apiFetch<GroupRow[]>(`/api/v1/closings/${id}/summary/payment-methods`),
        apiFetch<GroupRow[]>(`/api/v1/closings/${id}/summary/imported-expense-methods`),
        apiFetch<YogaAttribution>(`/api/v1/closings/${id}/summary/yoga-attribution`),
        apiFetch<Expense[]>(`/api/v1/closings/${id}/expenses`),
        apiFetch<Teacher[]>("/api/v1/teachers").catch(() => [] as Teacher[]),
        apiFetch<ImportBatch[]>(`/api/v1/closings/${id}/imports`),
        apiFetch<ImportBatch[]>(`/api/v1/closings/${id}/expense-imports`),
      ]);
      setClosing(c);
      setOverview(o);
      setCats(cc);
      setMethods(mm);
      setExpenseMethods(em);
      setYogaAttribution(ya);
      setExpenses(ex);
      setTeachers(tt);
      setImportBatches(imp);
      setExpenseImportBatches(eimp);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "Error al cargar.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (teachers.length > 0 && !teacherId) {
      setTeacherId(teachers[0].id);
    }
  }, [teachers, teacherId]);

  async function onIncomeFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f || !id) return;
    setUploadIncomeBusy(true);
    setMsg(null);
    setErr(null);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const res = await fetch(`/api/v1/closings/${id}/imports`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("almas_token")}`,
        },
        body: fd,
      });
      const text = await res.text();
      if (!res.ok) {
        const j = text ? JSON.parse(text) : {};
        throw new Error(j.detail || res.statusText);
      }
      const data = JSON.parse(text) as { lines_imported: number; rows_skipped: number };
      setMsg(`Importadas ${data.lines_imported} líneas (${data.rows_skipped} filas sin importe omitidas).`);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Error en la importación.");
    } finally {
      setUploadIncomeBusy(false);
    }
  }

  async function onExpenseFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f || !id) return;
    setUploadExpenseBusy(true);
    setMsg(null);
    setErr(null);
    try {
      const fd = new FormData();
      fd.append("file", f);
      const res = await fetch(`/api/v1/closings/${id}/expense-imports`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("almas_token")}`,
        },
        body: fd,
      });
      const text = await res.text();
      if (!res.ok) {
        const j = text ? JSON.parse(text) : {};
        throw new Error(j.detail || res.statusText);
      }
      const data = JSON.parse(text) as {
        lines_imported: number;
        rows_skipped: number;
        row_errors: string[];
      };
      const warn =
        data.row_errors?.length > 0
          ? ` Advertencias: ${data.row_errors.slice(0, 3).join(" ")}${data.row_errors.length > 3 ? "…" : ""}`
          : "";
      setMsg(
        `Gastos: importadas ${data.lines_imported} líneas (${data.rows_skipped} filas sin importe omitidas).${warn}`,
      );
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Error en la importación de gastos.");
    } finally {
      setUploadExpenseBusy(false);
    }
  }

  async function removeImportBatch(batchId: string, filename: string) {
    if (!id) return;
    if (
      !confirm(
        `¿Eliminar la importación "${filename}"? Se quitarán todas las líneas de pago de ese archivo del cierre. Los gastos manuales no se modifican.`
      )
    ) {
      return;
    }
    setErr(null);
    setMsg(null);
    setDeletingId(batchId);
    try {
      await apiFetch(`/api/v1/closings/${id}/imports/${batchId}`, { method: "DELETE" });
      setMsg("Importación eliminada.");
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "No se pudo eliminar la importación.");
    } finally {
      setDeletingId(null);
    }
  }

  async function removeExpenseImportBatch(batchId: string, filename: string) {
    if (!id) return;
    if (
      !confirm(
        `¿Eliminar la importación de gastos "${filename}"? Se quitarán todas las líneas de ese archivo. Los ingresos SigueFit y los gastos manuales no se modifican.`,
      )
    ) {
      return;
    }
    setErr(null);
    setMsg(null);
    setDeletingExpenseId(batchId);
    try {
      await apiFetch(`/api/v1/closings/${id}/expense-imports/${batchId}`, { method: "DELETE" });
      setMsg("Importación de gastos eliminada.");
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "No se pudo eliminar la importación de gastos.");
    } finally {
      setDeletingExpenseId(null);
    }
  }

  async function addExpense(e: React.FormEvent) {
    e.preventDefault();
    if (!id) return;
    setErr(null);
    try {
      const body =
        expenseType === "service"
          ? {
              expense_type: "service",
              amount,
              expense_date: expenseDate,
              vendor_or_teacher_name: vendor,
              description: description || null,
            }
          : {
              expense_type: "teacher_hours",
              amount,
              expense_date: expenseDate,
              teacher_id: teacherId,
              hours,
              hourly_rate: hourlyRate,
              description: description || null,
            };
      await apiFetch(`/api/v1/closings/${id}/expenses`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      setVendor("");
      setHours("");
      setHourlyRate("");
      setAmount("");
      setDescription("");
      setMsg("Gasto registrado.");
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "No se pudo guardar el gasto.");
    }
  }

  async function toggleFinalized() {
    if (!closing || !id) return;
    const next = closing.status === "finalized" ? "draft" : "finalized";
    if (next === "draft" && me?.role !== "admin") {
      setErr("Solo administradores pueden reabrir un cierre.");
      return;
    }
    try {
      await apiFetch(`/api/v1/closings/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: next }),
      });
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "No se pudo actualizar el estado.");
    }
  }

  async function removeExpense(expenseId: string) {
    if (!confirm("¿Eliminar este gasto?")) return;
    try {
      await apiFetch(`/api/v1/expenses/${expenseId}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "No se pudo eliminar.");
    }
  }

  if (!closing && !err) {
    return <p className="text-slate-600">Cargando…</p>;
  }
  if (!closing) {
    return (
      <div>
        <p className="text-red-600">{err}</p>
        <Link to="/" className="text-brand-700 text-sm mt-2 inline-block">
          Volver
        </Link>
      </div>
    );
  }

  const isFinal = closing.status === "finalized";
  const totalAbs = cats.reduce((s, r) => s + Math.abs(Number(r.total_amount)), 0) || 1;

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link to="/" className="text-sm text-brand-700 hover:underline">
            ← Cierres
          </Link>
          <h1 className="text-2xl font-semibold text-slate-900 mt-2">
            {months[closing.month - 1]} {closing.year}
          </h1>
          <p className="text-sm text-slate-600">
            Estado:{" "}
            <span className={isFinal ? "text-emerald-700 font-medium" : "text-amber-800 font-medium"}>
              {isFinal ? "Finalizado" : "Borrador"}
            </span>
          </p>
        </div>
        <button
          type="button"
          onClick={() => void toggleFinalized()}
          className="rounded-lg border border-slate-200 px-4 py-2 text-sm hover:bg-slate-50"
        >
          {isFinal ? "Reabrir borrador" : "Finalizar cierre"}
        </button>
      </div>

      {msg && <p className="text-sm text-emerald-800 bg-emerald-50 border border-emerald-100 rounded-lg px-3 py-2">{msg}</p>}
      {err && <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{err}</p>}

      {overview && (
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Total neto</p>
            <p className="text-lg font-semibold tabular-nums">
              <CurrencyARS value={overview.total_amount} />
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Ingresos (+)</p>
            <p className="text-lg font-semibold tabular-nums text-emerald-800">
              <CurrencyARS value={overview.positive_total} />
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Ajustes (-)</p>
            <p className="text-lg font-semibold tabular-nums text-red-700">
              <CurrencyARS value={overview.negative_total} />
            </p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs text-slate-500">Clientes (distintos)</p>
            <p className="text-lg font-semibold">{overview.distinct_clients}</p>
          </div>
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <h2 className="text-sm font-medium text-slate-800 px-4 py-3 border-b border-slate-100">
          Ganancia local — Irene y Mercedes (50% / 50%)
        </h2>
        <p className="text-xs text-slate-600 px-4 py-2 border-b border-slate-100 bg-slate-50/80">
          Se toma el <strong>saldo total</strong> del resumen por medio de pago y se divide en dos partes iguales. Lo que
          ya figura como saldo en <strong>{IRENE_METHOD}</strong> o en <strong>{MERCEDES_BUCKET}</strong> (incluye Lea)
          cuenta como transferencia de cada una. El resto (efectivo, Raquel y otros medios) forma un{" "}
          <strong>pool</strong> para completar la meta del 50%: primero se asigna al pool a quien tenga{" "}
          <strong>menor saldo en transferencia</strong>, hasta cubrir lo que le falte para su parte.
        </p>
        <div className="px-4 py-3 border-b border-slate-100 flex flex-wrap gap-4 text-sm">
          <div>
            <span className="text-slate-500">Saldo total a repartir: </span>
            <span className="font-semibold tabular-nums">{formatArs(partnerProfitSplit.totalSaldo)}</span>
          </div>
          <div>
            <span className="text-slate-500">Meta cada una (50%): </span>
            <span className="font-semibold tabular-nums text-brand-900">{formatArs(partnerProfitSplit.metaCadaUna)}</span>
          </div>
          <div>
            <span className="text-slate-500">Pool (efectivo + otros medios): </span>
            <span className="font-semibold tabular-nums">{formatArs(partnerProfitSplit.pool)}</span>
          </div>
          {partnerProfitSplit.poolRestante !== 0 && (
            <div>
              <span className="text-slate-500">Pool no asignado: </span>
              <span className="font-semibold tabular-nums text-amber-800">
                {formatArs(partnerProfitSplit.poolRestante)}
              </span>
            </div>
          )}
        </div>
        <div className="grid sm:grid-cols-2 gap-4 p-4">
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900 mb-3">Irene</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-2">
                <dt className="text-slate-600">Meta (50%)</dt>
                <dd className="tabular-nums font-medium">{formatArs(partnerProfitSplit.irene.meta)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-slate-600">Ya en transferencia ({IRENE_METHOD})</dt>
                <dd className="tabular-nums text-emerald-900">{formatArs(partnerProfitSplit.irene.transferencia)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-slate-600">Complemento desde pool</dt>
                <dd className="tabular-nums text-slate-900">{formatArs(partnerProfitSplit.irene.desdePool)}</dd>
              </div>
              <div className="flex justify-between gap-2 pt-2 border-t border-slate-100">
                <dt className="text-slate-800 font-medium">Total atribuido</dt>
                <dd className="tabular-nums font-semibold text-brand-900">{formatArs(partnerProfitSplit.irene.total)}</dd>
              </div>
            </dl>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-slate-900 mb-3">Mercedes</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-2">
                <dt className="text-slate-600">Meta (50%)</dt>
                <dd className="tabular-nums font-medium">{formatArs(partnerProfitSplit.mercedes.meta)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-slate-600">Ya en transferencia ({MERCEDES_BUCKET})</dt>
                <dd className="tabular-nums text-emerald-900">{formatArs(partnerProfitSplit.mercedes.transferencia)}</dd>
              </div>
              <div className="flex justify-between gap-2">
                <dt className="text-slate-600">Complemento desde pool</dt>
                <dd className="tabular-nums text-slate-900">{formatArs(partnerProfitSplit.mercedes.desdePool)}</dd>
              </div>
              <div className="flex justify-between gap-2 pt-2 border-t border-slate-100">
                <dt className="text-slate-800 font-medium">Total atribuido</dt>
                <dd className="tabular-nums font-semibold text-brand-900">
                  {formatArs(partnerProfitSplit.mercedes.total)}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <h2 className="text-sm font-medium text-slate-800 px-4 py-3 border-b border-slate-100">
          Resumen por medio de pago
        </h2>
        <p className="text-xs text-slate-600 px-4 py-2 border-b border-slate-100 bg-slate-50/80">
          Ingresos: totales SigueFit por método. Egresos: importación de gastos por medio.{" "}
          <span className="font-medium text-slate-700">
            Transferencia Lea se suma bajo {MERCEDES_BUCKET}.
          </span>{" "}
          Saldo = ingresos − egresos.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[32rem]">
            <thead className="bg-slate-50 text-left text-xs text-slate-600">
              <tr>
                <th className="px-4 py-2">Método de pago</th>
                <th className="px-4 py-2 text-right">Ingresos</th>
                <th className="px-4 py-2 text-right">Egresos</th>
                <th className="px-4 py-2 text-right">Saldo</th>
              </tr>
            </thead>
            <tbody>
              {methodCashflowRows.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-6 text-slate-500 text-center">
                    Sin datos en métodos de ingreso ni egreso importados.
                  </td>
                </tr>
              )}
              {methodCashflowRows.map((row) => (
                <tr key={row.label} className="border-t border-slate-100">
                  <td className="px-4 py-2 text-slate-800 font-medium">{row.label}</td>
                  <td className="px-4 py-2 text-right tabular-nums text-emerald-900">
                    {formatArs(row.ingresos)}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums text-red-800">
                    {formatArs(row.egresos)}
                  </td>
                  <td
                    className={`px-4 py-2 text-right tabular-nums font-semibold ${
                      row.saldo >= 0 ? "text-slate-900" : "text-red-700"
                    }`}
                  >
                    {formatArs(row.saldo)}
                  </td>
                </tr>
              ))}
            </tbody>
            {methodCashflowRows.length > 0 && (
              <tfoot className="bg-slate-50 border-t-2 border-slate-200">
                <tr>
                  <td className="px-4 py-3 text-sm font-medium text-slate-800">Total</td>
                  <td className="px-4 py-3 text-right text-sm font-semibold tabular-nums text-emerald-900">
                    {formatArs(methodCashflowTotals.ingresos)}
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-semibold tabular-nums text-red-800">
                    {formatArs(methodCashflowTotals.egresos)}
                  </td>
                  <td
                    className={`px-4 py-3 text-right text-sm font-semibold tabular-nums ${
                      methodCashflowTotals.saldo >= 0 ? "text-slate-900" : "text-red-700"
                    }`}
                  >
                    {formatArs(methodCashflowTotals.saldo)}
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </section>

      <section className="grid md:grid-cols-2 gap-6">
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <h2 className="text-sm font-medium text-slate-800 px-4 py-3 border-b border-slate-100">
            Por categoría de pago
          </h2>
          <div className="max-h-80 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs text-slate-600">
                <tr>
                  <th className="px-4 py-2">Categoría</th>
                  <th className="px-4 py-2 text-right">Total</th>
                  <th className="px-4 py-2 text-right">%</th>
                </tr>
              </thead>
              <tbody>
                {cats.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-6 text-slate-500 text-center">
                      Sin datos. Importá un Excel de SigueFit.
                    </td>
                  </tr>
                )}
                {cats.map((r) => (
                  <tr key={r.key} className="border-t border-slate-100">
                    <td className="px-4 py-2 text-slate-800 max-w-[10rem] truncate" title={r.key}>
                      {r.key || "—"}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      <CurrencyARS value={r.total_amount} />
                    </td>
                    <td className="px-4 py-2 text-right text-slate-500">
                      {Math.round((Math.abs(Number(r.total_amount)) / totalAbs) * 100)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <h2 className="text-sm font-medium text-slate-800 px-4 py-3 border-b border-slate-100">
            Por método de pago
          </h2>
          <div className="max-h-80 overflow-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-left text-xs text-slate-600">
                <tr>
                  <th className="px-4 py-2">Método</th>
                  <th className="px-4 py-2 text-right">Total</th>
                  <th className="px-4 py-2 text-right">Líneas</th>
                </tr>
              </thead>
              <tbody>
                {methods.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-6 text-slate-500 text-center">
                      Sin datos.
                    </td>
                  </tr>
                )}
                {methods.map((r) => (
                  <tr key={r.key} className="border-t border-slate-100">
                    <td className="px-4 py-2 text-slate-800 max-w-[10rem] truncate" title={r.key}>
                      {r.key || "—"}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      <CurrencyARS value={r.total_amount} />
                    </td>
                    <td className="px-4 py-2 text-right text-slate-500">{r.line_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <h2 className="text-sm font-medium text-slate-800 px-4 py-3 border-b border-slate-100">
          Ingreso atribuido a Yoga (por línea SigueFit)
        </h2>
        <p className="text-xs text-slate-600 px-4 py-2 border-b border-slate-100 bg-slate-50/80">
          Solo líneas cuya categoría de pago coincide con una regla configurada. El importe mostrado es el atribuido a
          Yoga según la regla indicada.
        </p>
        <div className="max-h-96 overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs text-slate-600 sticky top-0">
              <tr>
                <th className="px-4 py-2">Fecha</th>
                <th className="px-4 py-2">Cliente</th>
                <th className="px-4 py-2">Categoría</th>
                <th className="px-4 py-2 text-right">Importe</th>
                <th className="px-4 py-2">Regla</th>
                <th className="px-4 py-2 text-right">Yoga atribuido</th>
              </tr>
            </thead>
            <tbody>
              {yogaAttribution && yogaAttribution.items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-slate-500 text-center">
                    No hay líneas con categorías de Yoga configuradas. Importá SigueFit y verificá los nombres de categoría.
                  </td>
                </tr>
              )}
              {yogaAttribution?.items.map((row) => (
                <tr key={row.line_id} className="border-t border-slate-100">
                  <td className="px-4 py-2 text-slate-700 whitespace-nowrap">
                    {row.payment_date ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-slate-800 max-w-[8rem] truncate" title={row.client_name ?? ""}>
                    {row.client_name ?? "—"}
                  </td>
                  <td className="px-4 py-2 text-slate-800 max-w-[12rem] truncate" title={row.payment_category}>
                    {row.payment_category || "—"}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    <CurrencyARS value={row.amount} />
                  </td>
                  <td className="px-4 py-2 text-xs text-slate-600 max-w-[10rem]" title={row.rule_label}>
                    {row.rule_label}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums font-medium text-brand-900">
                    <CurrencyARS value={row.yoga_amount} />
                  </td>
                </tr>
              ))}
            </tbody>
            {yogaAttribution && yogaAttribution.items.length > 0 && (
              <tfoot className="bg-slate-50 border-t-2 border-slate-200 sticky bottom-0">
                <tr>
                  <td colSpan={5} className="px-4 py-3 text-right text-sm font-medium text-slate-800">
                    Total Yoga atribuido
                  </td>
                  <td className="px-4 py-3 text-right text-sm font-semibold tabular-nums text-brand-900">
                    <CurrencyARS value={yogaAttribution.total_yoga} />
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <h2 className="text-sm font-medium text-slate-800 px-4 py-3 border-b border-slate-100">
          Gastos importados por medio de pago
        </h2>
        <div className="max-h-80 overflow-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs text-slate-600">
              <tr>
                <th className="px-4 py-2">Medio</th>
                <th className="px-4 py-2 text-right">Total</th>
                <th className="px-4 py-2 text-right">Líneas</th>
              </tr>
            </thead>
            <tbody>
              {expenseMethods.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-slate-500 text-center">
                    Sin datos. Importá un Excel de gastos (Importe + método/medio de pago permitido).
                  </td>
                </tr>
              )}
              {expenseMethods.map((r) => (
                <tr key={r.key} className="border-t border-slate-100">
                  <td className="px-4 py-2 text-slate-800 max-w-[10rem] truncate" title={r.key}>
                    {r.key || "—"}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">
                    <CurrencyARS value={r.total_amount} />
                  </td>
                  <td className="px-4 py-2 text-right text-slate-500">{r.line_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-dashed border-brand-300 bg-brand-50/40 p-6 space-y-8">
        <div>
          <h2 className="text-sm font-medium text-slate-800 mb-2">Importar ingresos SigueFit (.xlsx)</h2>
          <p className="text-xs text-slate-600 mb-4">
            Exportá “Pagos / detalle” desde SigueFit y subí el archivo. Se detectan columnas por nombre.
          </p>
          <label
            className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium text-white cursor-pointer ${
              isFinal || uploadIncomeBusy ? "bg-slate-400 cursor-not-allowed" : "bg-brand-700 hover:bg-brand-900"
            }`}
          >
            {uploadIncomeBusy ? "Procesando…" : "Elegir archivo (ingresos)"}
            <input
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              className="hidden"
              disabled={isFinal || uploadIncomeBusy}
              onChange={(ev) => void onIncomeFile(ev)}
            />
          </label>
        </div>

        <div className="pt-2 border-t border-brand-200/80">
          <h2 className="text-sm font-medium text-slate-800 mb-2">Importar gastos (.xlsx)</h2>
          <p className="text-xs text-slate-600 mb-4">
            Mismo formato tabular con columnas <strong>Importe</strong> y <strong>Método de Pago</strong> o{" "}
            <strong>Medio de pago</strong>. Solo se importan medios: Efectivo, Transferencia Irene, Lea, Mercedes o
            Raquel.
          </p>
          <label
            className={`inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium text-white cursor-pointer ${
              isFinal || uploadExpenseBusy ? "bg-slate-400 cursor-not-allowed" : "bg-slate-800 hover:bg-slate-950"
            }`}
          >
            {uploadExpenseBusy ? "Procesando…" : "Elegir archivo (gastos)"}
            <input
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              className="hidden"
              disabled={isFinal || uploadExpenseBusy}
              onChange={(ev) => void onExpenseFile(ev)}
            />
          </label>
        </div>

        {isFinal && (
          <p className="text-xs text-amber-800">Cierre finalizado: no se pueden nuevas importaciones.</p>
        )}

        {importBatches.length > 0 && (
          <div className="pt-4 border-t border-brand-200/80">
            <h3 className="text-xs font-medium text-slate-700 mb-2">Archivos SigueFit (ingresos)</h3>
            <p className="text-xs text-slate-600 mb-3">
              Podés quitar un Excel cargado mientras el cierre esté en borrador; los resúmenes se actualizan y podés volver
              a subir el mismo archivo si hace falta.
            </p>
            <ul className="space-y-2">
              {importBatches.map((b) => (
                <li
                  key={b.id}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-lg bg-white/80 border border-slate-200 px-3 py-2 text-sm"
                >
                  <div className="min-w-0">
                    <p className="font-medium text-slate-900 truncate" title={b.original_filename}>
                      {b.original_filename}
                    </p>
                    <p className="text-xs text-slate-500">
                      {new Date(b.uploaded_at).toLocaleString("es-AR", {
                        dateStyle: "short",
                        timeStyle: "short",
                      })}
                    </p>
                  </div>
                  {!isFinal && (
                    <button
                      type="button"
                      className="text-xs text-red-700 hover:underline shrink-0 disabled:opacity-50"
                      disabled={deletingId === b.id}
                      onClick={() => void removeImportBatch(b.id, b.original_filename)}
                    >
                      {deletingId === b.id ? "Eliminando…" : "Eliminar"}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}

        {expenseImportBatches.length > 0 && (
          <div className="pt-4 border-t border-brand-200/80">
            <h3 className="text-xs font-medium text-slate-700 mb-2">Archivos de gastos importados</h3>
            <p className="text-xs text-slate-600 mb-3">
              Eliminá un archivo equivocado en borrador; el resumen “Gastos importados por medio de pago” se actualiza.
            </p>
            <ul className="space-y-2">
              {expenseImportBatches.map((b) => (
                <li
                  key={b.id}
                  className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-lg bg-white/80 border border-slate-200 px-3 py-2 text-sm"
                >
                  <div className="min-w-0">
                    <p className="font-medium text-slate-900 truncate" title={b.original_filename}>
                      {b.original_filename}
                    </p>
                    <p className="text-xs text-slate-500">
                      {new Date(b.uploaded_at).toLocaleString("es-AR", {
                        dateStyle: "short",
                        timeStyle: "short",
                      })}
                    </p>
                  </div>
                  {!isFinal && (
                    <button
                      type="button"
                      className="text-xs text-red-700 hover:underline shrink-0 disabled:opacity-50"
                      disabled={deletingExpenseId === b.id}
                      onClick={() => void removeExpenseImportBatch(b.id, b.original_filename)}
                    >
                      {deletingExpenseId === b.id ? "Eliminando…" : "Eliminar"}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm space-y-4">
        <h2 className="text-sm font-medium text-slate-800">Gastos manuales</h2>
        <form onSubmit={addExpense} className="space-y-3 border border-slate-100 rounded-lg p-4 bg-slate-50/80">
          <div className="flex gap-2 flex-wrap">
            <button
              type="button"
              className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                expenseType === "service" ? "bg-brand-700 text-white" : "bg-white border border-slate-200"
              }`}
              onClick={() => setExpenseType("service")}
              disabled={isFinal}
            >
              Servicio
            </button>
            <button
              type="button"
              className={`rounded-lg px-3 py-1.5 text-xs font-medium ${
                expenseType === "teacher_hours" ? "bg-brand-700 text-white" : "bg-white border border-slate-200"
              }`}
              onClick={() => setExpenseType("teacher_hours")}
              disabled={isFinal}
            >
              Horas docente
            </button>
          </div>
          {expenseType === "service" ? (
            <div>
              <label className="block text-xs text-slate-500 mb-1">Proveedor / concepto</label>
              <input
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={vendor}
                onChange={(e) => setVendor(e.target.value)}
                required
                disabled={isFinal}
              />
            </div>
          ) : (
            <div className="grid sm:grid-cols-3 gap-3">
              <div className="sm:col-span-3">
                <label className="block text-xs text-slate-500 mb-1">Profesora</label>
                <select
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  value={teacherId}
                  onChange={(e) => setTeacherId(e.target.value)}
                  required
                  disabled={isFinal || teachers.length === 0}
                >
                  {teachers.length === 0 && <option value="">Sin profesoras (cargar en menú)</option>}
                  {teachers.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.full_name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Horas</label>
                <input
                  type="number"
                  step="0.01"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  value={hours}
                  onChange={(e) => setHours(e.target.value)}
                  required
                  disabled={isFinal}
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Valor hora</label>
                <input
                  type="number"
                  step="0.01"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  value={hourlyRate}
                  onChange={(e) => setHourlyRate(e.target.value)}
                  required
                  disabled={isFinal}
                />
              </div>
            </div>
          )}
          <div className="grid sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Monto total</label>
              <input
                type="number"
                step="0.01"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
                disabled={isFinal}
              />
              {expenseType === "teacher_hours" && hours && hourlyRate && (
                <p className="text-xs text-slate-500 mt-1">
                  Verificación: {formatArs(Number(hours) * Number(hourlyRate))}
                </p>
              )}
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Fecha</label>
              <input
                type="date"
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={expenseDate}
                onChange={(e) => setExpenseDate(e.target.value)}
                required
                disabled={isFinal}
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Nota (opcional)</label>
            <input
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isFinal}
            />
          </div>
          <button
            type="submit"
            disabled={isFinal}
            className="rounded-lg bg-slate-900 text-white px-4 py-2 text-sm disabled:opacity-40"
          >
            Agregar gasto
          </button>
        </form>

        <ul className="divide-y divide-slate-100">
          {expenses.length === 0 && <li className="py-4 text-sm text-slate-500">No hay gastos cargados.</li>}
          {expenses.map((x) => (
            <li key={x.id} className="py-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <div>
                <p className="font-medium text-slate-900">
                  {x.expense_type === "service" ? "Servicio" : "Horas docente"} —{" "}
                  {x.vendor_or_teacher_name || "—"}
                </p>
                <p className="text-xs text-slate-500">
                  {x.expense_date}
                  {x.hours && x.hourly_rate && (
                    <span>
                      {" "}
                      · {x.hours} h × {formatArs(x.hourly_rate)}
                    </span>
                  )}
                </p>
                {x.description && <p className="text-xs text-slate-600 mt-0.5">{x.description}</p>}
              </div>
              <div className="flex items-center gap-3">
                <span className="font-semibold tabular-nums">
                  <CurrencyARS value={x.amount} />
                </span>
                {!isFinal && (
                  <button
                    type="button"
                    className="text-xs text-red-600 hover:underline"
                    onClick={() => void removeExpense(x.id)}
                  >
                    Eliminar
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
