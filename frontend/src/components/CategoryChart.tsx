import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from "recharts";
import type { Metrics } from "../types";
import { formatInr } from "../lib/format";

const COLORS = [
  "#6366f1", // Indigo
  "#10b981", // Emerald
  "#f59e0b", // Amber
  "#ef4444", // Red
  "#06b6d4", // Cyan
  "#8b5cf6", // Purple
  "#ec4899", // Pink
  "#84cc16", // Lime
  "#f97316", // Orange
  "#64748b", // Slate
];

export default function CategoryChart({ metrics }: { metrics: Metrics }) {
  const data = metrics.top_categories.map(([name, value]) => ({ name, value }));
  const totalSpend = metrics.total_spend;
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-100 flex flex-col justify-between min-h-[360px]">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-base font-semibold text-slate-900">Spending by Category</h2>
          <p className="text-xs text-slate-400">Horizontal distribution of expenses</p>
        </div>
        <div className="text-right">
          <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-400 block">Total Spend</span>
          <span className="text-base font-bold text-slate-800">{formatInr(totalSpend)}</span>
        </div>
      </div>

      {data.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-slate-400">No spending data to display.</p>
        </div>
      ) : (
        <div className="h-[280px] w-full flex-1">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f8fafc" />
              <XAxis
                type="number"
                tickFormatter={(val) => `₹${val}`}
                stroke="#94a3b8"
                fontSize={10}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#475569"
                fontSize={12}
                fontWeight={500}
                tickLine={false}
                axisLine={false}
                width={100}
              />
              <Tooltip
                cursor={{ fill: "#f8fafc" }}
                formatter={(value) => [formatInr(Number(value)), "Spend"]}
                contentStyle={{
                  backgroundColor: "#fff",
                  border: "1px solid #e2e8f0",
                  borderRadius: "12px",
                  fontSize: "12px",
                  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                }}
              />
              <Bar
                dataKey="value"
                radius={[0, 6, 6, 0]}
                barSize={16}
                onMouseEnter={(_, index) => setActiveIndex(index)}
                onMouseLeave={() => setActiveIndex(null)}
              >
                {data.map((_, i) => (
                  <Cell
                    key={i}
                    fill={COLORS[i % COLORS.length]}
                    style={{
                      opacity: activeIndex === null || activeIndex === i ? 1 : 0.6,
                      transition: "opacity 200ms ease-in-out",
                      cursor: "pointer",
                    }}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
