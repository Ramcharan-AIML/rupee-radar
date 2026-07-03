import type { Metrics } from "../types";
import { formatInr, formatPct } from "../lib/format";

function Card({
  label,
  value,
  sub,
  tone = "slate",
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "slate" | "green" | "red" | "indigo";
}) {
  const toneClass = {
    slate: "text-slate-900",
    green: "text-green-600",
    red: "text-red-600",
    indigo: "text-indigo-600",
  }[tone];
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${toneClass}`}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
    </div>
  );
}

export default function SummaryCards({ metrics }: { metrics: Metrics }) {
  const savingsTone = metrics.net_savings >= 0 ? "green" : "red";
  const biggest = metrics.biggest_transaction;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card label="Total Income" value={formatInr(metrics.total_income)} tone="green" />
      <Card label="Total Spend" value={formatInr(metrics.total_spend)} tone="red" />
      <Card
        label="Net Savings"
        value={formatInr(metrics.net_savings)}
        sub={metrics.total_income > 0 ? `${formatPct(metrics.savings_rate)} of income` : "no income detected"}
        tone={savingsTone}
      />
      <Card
        label="Biggest Expense"
        value={biggest ? formatInr(biggest.amount) : "—"}
        sub={biggest ? biggest.description_clean : undefined}
        tone="indigo"
      />
    </div>
  );
}
