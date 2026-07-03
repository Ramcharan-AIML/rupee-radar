import type { Metrics } from "../types";
import { formatInr, formatPct } from "../lib/format";

interface CardProps {
  label: string;
  value: string;
  sub?: string;
  icon: string;
  gradient: string;
  textColor: string;
}

function Card({ label, value, sub, icon, gradient, textColor }: CardProps) {
  return (
    <div className={`rounded-2xl p-5 shadow-sm ring-1 ring-slate-100 bg-gradient-to-br from-white ${gradient} hover:-translate-y-0.5 hover:shadow-md hover:ring-slate-200 transition-all duration-200 cursor-default flex flex-col justify-between min-h-[125px]`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p>
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white/80 backdrop-blur-sm shadow-xs border border-slate-100 text-sm">
          {icon}
        </span>
      </div>
      <div>
        <p className={`text-2xl font-bold tracking-tight mt-3 ${textColor}`}>{value}</p>
        {sub && <p className="mt-1 text-[11px] font-medium text-slate-400 truncate">{sub}</p>}
      </div>
    </div>
  );
}

export default function SummaryCards({ metrics }: { metrics: Metrics }) {
  const savingsTone = metrics.net_savings >= 0;
  const biggest = metrics.biggest_transaction;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Card
        label="Total Income"
        value={formatInr(metrics.total_income)}
        icon="📈"
        gradient="to-emerald-50/25"
        textColor="text-emerald-600"
      />
      <Card
        label="Total Spend"
        value={formatInr(metrics.total_spend)}
        icon="📉"
        gradient="to-rose-50/25"
        textColor="text-rose-600"
      />
      <Card
        label="Net Savings"
        value={formatInr(metrics.net_savings)}
        sub={metrics.total_income > 0 ? `${formatPct(metrics.savings_rate)} of income` : "no income detected"}
        icon="🏦"
        gradient={savingsTone ? "to-emerald-50/25" : "to-rose-50/25"}
        textColor={savingsTone ? "text-emerald-600" : "text-rose-600"}
      />
      <Card
        label="Biggest Expense"
        value={biggest ? formatInr(biggest.amount) : "—"}
        sub={biggest ? biggest.description_clean : undefined}
        icon="🏷️"
        gradient="to-indigo-50/25"
        textColor="text-indigo-600"
      />
    </div>
  );
}
