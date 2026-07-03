import type { RecurringGroup } from "../types";
import { formatInr } from "../lib/format";

const CADENCE_COLORS: Record<string, string> = {
  weekly: "bg-purple-50 text-purple-700 ring-1 ring-purple-600/10",
  monthly: "bg-indigo-50 text-indigo-700 ring-1 ring-indigo-600/10",
  quarterly: "bg-cyan-50 text-cyan-700 ring-1 ring-cyan-600/10",
  yearly: "bg-teal-50 text-teal-700 ring-1 ring-teal-600/10",
  irregular: "bg-amber-50 text-amber-700 ring-1 ring-amber-600/10",
};

const CATEGORY_COLORS: Record<string, string> = {
  Food: "bg-amber-100 text-amber-700",
  Travel: "bg-cyan-100 text-cyan-700",
  Shopping: "bg-pink-100 text-pink-700",
  Bills: "bg-blue-100 text-blue-700",
  EMI: "bg-red-100 text-red-700",
  Subscriptions: "bg-purple-100 text-purple-700",
  Salary: "bg-green-100 text-green-700",
  Rent: "bg-orange-100 text-orange-700",
  Investments: "bg-lime-100 text-lime-700",
  Other: "bg-slate-100 text-slate-600",
};

export default function RecurringTable({ recurring }: { recurring: RecurringGroup[] }) {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <h2 className="text-sm font-semibold text-slate-700 mb-4">
        Detected Recurring Payments{" "}
        <span className="font-normal text-slate-400">
          ({recurring.length} active stream{recurring.length !== 1 && "s"})
        </span>
      </h2>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-400">
              <th className="py-2 pr-4">Merchant / Stream</th>
              <th className="py-2 pr-4">Category</th>
              <th className="py-2 pr-4">Cadence</th>
              <th className="py-2 pr-4 text-center">Occurrences</th>
              <th className="py-2 pr-4 text-right">Typical Amount</th>
            </tr>
          </thead>
          <tbody>
            {recurring.map((item) => (
              <tr key={item.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/40">
                <td className="py-3 pr-4 font-semibold text-slate-800">{item.merchant}</td>
                <td className="py-3 pr-4">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      CATEGORY_COLORS[item.category] ?? CATEGORY_COLORS.Other
                    }`}
                  >
                    {item.category}
                  </span>
                </td>
                <td className="py-3 pr-4">
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs font-semibold capitalize ${
                      CADENCE_COLORS[item.cadence] ?? CADENCE_COLORS.irregular
                    }`}
                  >
                    {item.cadence}
                  </span>
                </td>
                <td className="py-3 pr-4 text-center text-slate-600 tabular-nums">{item.occurrences}x</td>
                <td className="py-3 pr-4 text-right font-semibold text-slate-800 tabular-nums">
                  {formatInr(item.typical_amount)}
                </td>
              </tr>
            ))}
            {recurring.length === 0 && (
              <tr>
                <td colSpan={5} className="py-8 text-center text-sm text-slate-400">
                  No recurring payments (subscriptions, rent, EMIs) detected in this statement.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
