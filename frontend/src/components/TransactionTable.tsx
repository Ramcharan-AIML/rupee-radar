import { useMemo, useState } from "react";
import type { Transaction } from "../types";
import { formatDate, formatInr } from "../lib/format";

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

const PAGE_SIZE = 10;

export default function TransactionTable({ transactions }: { transactions: Transaction[] }) {
  const [query, setQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  const filtered = useMemo(() => {
    setCurrentPage(1); // Reset page on filter
    const q = query.trim().toLowerCase();
    if (!q) return transactions;
    return transactions.filter((t) =>
      `${t.description_clean} ${t.description_raw} ${t.category}`.toLowerCase().includes(q)
    );
  }, [transactions, query]);

  const pageCount = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filtered.slice(start, start + PAGE_SIZE);
  }, [filtered, currentPage]);

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100 flex flex-col justify-between min-h-[500px]">
      <div>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-5">
          <div>
            <h2 className="text-base font-semibold text-slate-800">
              Transactions History
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Showing {filtered.length} matching entries
            </p>
          </div>
          <div className="relative w-full sm:w-64">
            <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-slate-400">
              🔍
            </span>
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search merchant or category…"
              className="w-full rounded-xl bg-slate-50 hover:bg-slate-100/50 focus:bg-white text-sm outline-none border border-slate-100 focus:border-indigo-400 pl-9 pr-4 py-2 transition-colors"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm mt-3">
            <thead>
              <tr className="border-b border-slate-100 text-[10px] uppercase tracking-wider font-bold text-slate-400">
                <th className="py-3 pr-4">Date</th>
                <th className="py-3 pr-4">Merchant / Narration</th>
                <th className="py-3 pr-4">Category</th>
                <th className="py-3 pr-4 text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {paginated.map((t) => (
                <tr key={t.id} className="border-b border-slate-50 last:border-0 hover:bg-slate-50/20 transition-colors">
                  <td className="py-3 pr-4 whitespace-nowrap text-xs text-slate-500 font-medium">{formatDate(t.date)}</td>
                  <td className="py-3 pr-4">
                    <span className="font-semibold text-slate-700 block">{t.description_clean}</span>
                    <span className="text-[10px] text-slate-400 font-medium block truncate max-w-xs sm:max-w-md">{t.description_raw}</span>
                  </td>
                  <td className="py-3 pr-4">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-inset ${
                        CATEGORY_COLORS[t.category] ?? CATEGORY_COLORS.Other
                      }`}
                    >
                      {t.category}
                    </span>
                  </td>
                  <td
                    className={`py-3 pr-4 text-right font-bold tabular-nums ${
                      t.direction === "credit" ? "text-emerald-600" : "text-slate-700"
                    }`}
                  >
                    {t.direction === "credit" ? "+" : "−"}
                    {formatInr(t.amount, true)}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-12 text-center text-sm font-medium text-slate-400">
                    No transactions match your search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination controls */}
      {pageCount > 1 && (
        <div className="flex items-center justify-between border-t border-slate-100 pt-4 mt-4">
          <button
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-200 disabled:opacity-40 transition-colors cursor-pointer"
          >
            ← Previous
          </button>
          <span className="text-xs font-medium text-slate-500">
            Page {currentPage} of {pageCount}
          </span>
          <button
            onClick={() => setCurrentPage((p) => Math.min(pageCount, p + 1))}
            disabled={currentPage === pageCount}
            className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-bold text-slate-700 hover:bg-slate-200 disabled:opacity-40 transition-colors cursor-pointer"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
