import type { RecurringGroup } from "../types";
import { formatInr } from "../lib/format";

const CADENCE_COLORS: Record<string, string> = {
  weekly: "bg-purple-50 text-purple-700 ring-purple-600/10",
  monthly: "bg-indigo-50 text-indigo-700 ring-indigo-600/10",
  quarterly: "bg-cyan-50 text-cyan-700 ring-cyan-600/10",
  yearly: "bg-teal-50 text-teal-700 ring-teal-600/10",
  irregular: "bg-amber-50 text-amber-700 ring-amber-600/10",
};

const CATEGORY_COLORS: Record<string, string> = {
  Food: "bg-amber-50 text-amber-700 ring-amber-600/10",
  Travel: "bg-cyan-50 text-cyan-700 ring-cyan-600/10",
  Shopping: "bg-pink-50 text-pink-700 ring-pink-600/10",
  Bills: "bg-blue-50 text-blue-700 ring-blue-600/10",
  EMI: "bg-rose-50 text-rose-700 ring-rose-600/10",
  Subscriptions: "bg-purple-50 text-purple-700 ring-purple-600/10",
  Salary: "bg-emerald-50 text-emerald-700 ring-emerald-600/10",
  Rent: "bg-orange-50 text-orange-700 ring-orange-600/10",
  Investments: "bg-lime-50 text-lime-700 ring-lime-600/10",
  Other: "bg-slate-50 text-slate-600 ring-slate-600/10",
};

export default function RecurringTable({ recurring }: { recurring: RecurringGroup[] }) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-base font-semibold text-slate-800">Recurring Financial Streams</h2>
          <p className="text-xs text-slate-400 mt-0.5">Subscriptions, EMIs, salary, and routine transfers</p>
        </div>
        <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600">
          {recurring.length} Stream{recurring.length !== 1 && "s"} Identified
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-100 text-[10px] uppercase tracking-wider font-bold text-slate-400">
              <th className="py-3 pr-4">Merchant / Stream details</th>
              <th className="py-3 pr-4">Category</th>
              <th className="py-3 pr-4">Interval Cadence</th>
              <th className="py-3 pr-4 text-center">Occurrences</th>
              <th className="py-3 pr-4 text-right">Typical amount</th>
            </tr>
          </thead>
          <tbody>
            {recurring.map((item) => (
              <tr key={item.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/20 transition-colors">
                <td className="py-3.5 pr-4 font-bold text-slate-800">{item.merchant}</td>
                <td className="py-3.5 pr-4">
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${
                      CATEGORY_COLORS[item.category] ?? CATEGORY_COLORS.Other
                    }`}
                  >
                    {item.category}
                  </span>
                </td>
                <td className="py-3.5 pr-4">
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-bold capitalize ring-1 ring-inset ${
                      CADENCE_COLORS[item.cadence] ?? CADENCE_COLORS.irregular
                    }`}
                  >
                    {item.cadence}
                  </span>
                </td>
                <td className="py-3.5 pr-4 text-center text-slate-600 font-semibold tabular-nums">{item.occurrences}x</td>
                <td className="py-3.5 pr-4 text-right font-bold text-slate-800 tabular-nums">
                  {formatInr(item.typical_amount)}
                </td>
              </tr>
            ))}
            {recurring.length === 0 && (
              <tr>
                <td colSpan={5} className="py-12 text-center text-sm font-medium text-slate-400">
                  No recurring payments detected in this statement period.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
