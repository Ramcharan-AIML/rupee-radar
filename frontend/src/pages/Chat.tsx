import { useEffect, useState } from "react";
import ChatPanel from "../components/ChatPanel";
import { formatDate, formatInr } from "../lib/format";

interface HistoryItem {
  session_id: string;
  created_at: string;
  metrics: {
    total_spend: number;
    total_income: number;
  };
}

export default function Chat({ defaultSessionId }: { defaultSessionId?: string }) {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(defaultSessionId || null);

  useEffect(() => {
    async function loadHistory() {
      try {
        const res = await fetch("/api/history");
        if (res.ok) {
          const body = await res.json();
          setHistory(body);
          if (!selectedId && body.length > 0) {
            setSelectedId(body[0].session_id);
          }
        }
      } catch (err) {
        console.error("Failed to load upload history:", err);
      }
    }
    loadHistory();
  }, [selectedId]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
      {/* Sidebar - Statement Session Selector */}
      <div className="md:col-span-1 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100 flex flex-col h-[600px]">
        <h2 className="text-sm font-bold text-slate-800 mb-4 flex items-center gap-2 pb-3 border-b border-slate-50">
          <span>📁</span> Upload History
        </h2>

        <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 custom-scrollbar">
          {history.map((item) => {
            const isActive = item.session_id === selectedId;
            return (
              <button
                key={item.session_id}
                onClick={() => setSelectedId(item.session_id)}
                className={`w-full text-left p-3.5 rounded-xl border transition-all duration-200 cursor-pointer ${
                  isActive
                    ? "bg-indigo-50/50 border-indigo-200 text-indigo-950 shadow-xs"
                    : "bg-white border-slate-100 hover:bg-slate-50 hover:border-slate-200 text-slate-700"
                }`}
              >
                <div className="text-xs font-bold">{formatDate(item.created_at)}</div>
                <div className="text-[9px] text-slate-400 mt-0.5 truncate uppercase tracking-wider font-semibold">
                  ID: {item.session_id.substring(0, 8)}
                </div>
                <div className="flex items-center justify-between text-xs font-semibold mt-3 pt-2 border-t border-dashed border-slate-100">
                  <span className="text-slate-400">Total Spend:</span>
                  <span className={isActive ? "text-indigo-600 font-bold" : "text-slate-700 font-bold"}>
                    {formatInr(item.metrics.total_spend)}
                  </span>
                </div>
              </button>
            );
          })}
          {history.length === 0 && (
            <p className="text-center text-xs font-semibold text-slate-400 py-16 leading-relaxed">
              No uploaded statements<br />yet.
            </p>
          )}
        </div>
      </div>

      {/* Main Workspace - Active Chat Panel */}
      <div className="md:col-span-3">
        {selectedId ? (
          <ChatPanel key={selectedId} sessionId={selectedId} />
        ) : (
          <div className="flex items-center justify-center rounded-2xl bg-white shadow-sm ring-1 ring-slate-100 h-[600px]">
            <p className="text-slate-400 text-sm font-semibold">Please select a statement to start chatting.</p>
          </div>
        )}
      </div>
    </div>
  );
}
