export function formatArs(n: number | string) {
  const v = typeof n === "string" ? Number(n) : n;
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
  }).format(v);
}

export default function CurrencyARS({ value }: { value: number | string }) {
  return <span className="tabular-nums">{formatArs(value)}</span>;
}
