import { useMemo, useState } from "react";
import type { Transaction } from "../types";
import { formatDate, formatInr } from "../lib/format";

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

export default function TransactionTable({ transactions }: { transactions: Transaction[] }) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return transactions;
    return transactions.filter((t) =>
      `${t.description_clean} ${t.description_raw} ${t.category}`.toLowerCase().includes(q)
    );
  }, [transactions, query]);

  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-sm font-semibold text-slate-700">
          Transactions{" "}
          <span className="font-normal text-slate-400">
            ({filtered.length} of {transactions.length})
          </span>
        </h2>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search merchant or category…"
          className="w-full rounded-lg border border-slate-200 px-3 py-1.5 text-sm outline-none focus:border-indigo-400 sm:w-64"
        />
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-400">
              <th className="py-2 pr-4">Date</th>
              <th className="py-2 pr-4">Merchant</th>
              <th className="py-2 pr-4">Category</th>
              <th className="py-2 pr-4 text-right">Amount</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((t) => (
              <tr key={t.id} className="border-b border-slate-100 last:border-0">
                <td className="py-2 pr-4 whitespace-nowrap text-slate-500">{formatDate(t.date)}</td>
                <td className="py-2 pr-4">
                  <span className="font-medium text-slate-800">{t.description_clean}</span>
                </td>
                <td className="py-2 pr-4">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      CATEGORY_COLORS[t.category] ?? CATEGORY_COLORS.Other
                    }`}
                  >
                    {t.category}
                  </span>
                </td>
                <td
                  className={`py-2 pr-4 text-right font-medium tabular-nums ${
                    t.direction === "credit" ? "text-green-600" : "text-slate-800"
                  }`}
                >
                  {t.direction === "credit" ? "+" : "−"}
                  {formatInr(t.amount, true)}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={4} className="py-6 text-center text-slate-400">
                  No transactions match your search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
