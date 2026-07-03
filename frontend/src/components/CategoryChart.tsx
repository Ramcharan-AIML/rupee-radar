import { useState } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
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
    <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <h2 className="text-base font-semibold text-slate-900 mb-6">Spending by Category</h2>
      {data.length === 0 ? (
        <p className="py-12 text-center text-sm text-slate-400">No spending to chart.</p>
      ) : (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-8">
          {/* Donut Chart Container */}
          <div className="relative w-[200px] h-[200px] flex-shrink-0 flex items-center justify-center">
            {/* Center Label */}
            <div className="absolute flex flex-col items-center justify-center text-center pointer-events-none">
              <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
                Total Spend
              </span>
              <span className="text-lg font-bold text-slate-800 mt-0.5">
                {formatInr(totalSpend)}
              </span>
            </div>

            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={65}
                  outerRadius={85}
                  paddingAngle={2}
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
                        cursor: "pointer"
                      }}
                      className="outline-none"
                    />
                  ))}
                </Pie>
                <Tooltip 
                  formatter={(value) => formatInr(Number(value))}
                  contentStyle={{
                    backgroundColor: "rgba(15, 23, 42, 0.9)",
                    border: "none",
                    borderRadius: "8px",
                    color: "#fff",
                    fontSize: "12px",
                  }}
                  itemStyle={{ color: "#fff" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Details / Legend List */}
          <div className="w-full flex-1 max-h-[200px] overflow-y-auto pr-1 space-y-2 custom-scrollbar">
            {data.map((item, i) => {
              const percentage = totalSpend > 0 ? (item.value / totalSpend) * 100 : 0;
              const isHighlighted = activeIndex === i;
              return (
                <div
                  key={item.name}
                  className={`flex items-center justify-between p-2 rounded-xl transition-all duration-200 ${
                    isHighlighted ? "bg-slate-50 translate-x-1" : "hover:bg-slate-50/50"
                  }`}
                  onMouseEnter={() => setActiveIndex(i)}
                  onMouseLeave={() => setActiveIndex(null)}
                >
                  <div className="flex items-center gap-3">
                    <span 
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0 transition-transform duration-200" 
                      style={{ 
                        backgroundColor: COLORS[i % COLORS.length],
                        transform: isHighlighted ? "scale(1.25)" : "scale(1)"
                      }}
                    />
                    <span className="text-sm font-medium text-slate-700">{item.name}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-semibold text-slate-800">
                      {formatInr(item.value)}
                    </div>
                    <div className="text-[10px] font-medium text-slate-400">
                      {percentage.toFixed(1)}%
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

