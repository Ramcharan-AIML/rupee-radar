import { useEffect, useState } from "react";

interface UsageData {
  used: number;
  remaining: number;
  provider: string;
  degraded: boolean;
  per_minute: number;
  per_day: number;
}

export default function BudgetBadge() {
  const [data, setData] = useState<UsageData | null>(null);

  useEffect(() => {
    async function fetchUsage() {
      try {
        const res = await fetch("/api/usage");
        if (res.ok) {
          const body = await res.json();
          setData(body);
        }
      } catch (err) {
        console.error("Failed to load token usage stats:", err);
      }
    }
    fetchUsage();
    // Poll usage every 10 seconds for real-time tracking
    const interval = setInterval(fetchUsage, 10000);
    return () => clearInterval(interval);
  }, []);

  if (!data) return null;

  if (data.provider === "none") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-500 ring-1 ring-slate-500/10">
        <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
        LLM: Offline
      </span>
    );
  }

  const limit = data.used + data.remaining;
  const usagePercentage = limit > 0 ? (data.used / limit) : 0;

  if (data.degraded) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-semibold text-red-700 ring-1 ring-red-700/10">
        <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />
        LLM: Degraded
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700 ring-1 ring-green-700/10">
      <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
      LLM: {data.provider.toUpperCase()} ({Math.round(usagePercentage * 100)}% budget used)
    </span>
  );
}
