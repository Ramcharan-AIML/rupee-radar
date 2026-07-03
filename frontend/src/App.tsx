import { useState } from "react";
import Upload from "./pages/Upload";
import Dashboard from "./pages/Dashboard";
import Chat from "./pages/Chat";
import BudgetBadge from "./components/BudgetBadge";
import type { UploadResponse } from "./types";

export default function App() {
  const [data, setData] = useState<UploadResponse | null>(null);
  const [view, setView] = useState<"dashboard" | "chat">("dashboard");

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-xl">📡</span>
              <span className="text-lg font-bold tracking-tight text-slate-900">RupeeRadar</span>
              <span className="hidden text-xs text-slate-400 sm:inline font-medium">
                personal finance analyst
              </span>
            </div>
            <BudgetBadge />
          </div>

          {data && (
            <div className="flex items-center gap-4">
              <div className="flex bg-slate-100 p-0.5 rounded-xl text-xs font-semibold ring-1 ring-slate-200">
                <button
                  onClick={() => setView("dashboard")}
                  className={`px-3 py-1.5 rounded-lg transition-all duration-150 ${
                    view === "dashboard"
                      ? "bg-white text-slate-800 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  Dashboard
                </button>
                <button
                  onClick={() => setView("chat")}
                  className={`px-3 py-1.5 rounded-lg transition-all duration-150 ${
                    view === "chat"
                      ? "bg-white text-slate-800 shadow-sm"
                      : "text-slate-500 hover:text-slate-700"
                  }`}
                >
                  Analyst Chat
                </button>
              </div>
              <button
                onClick={() => {
                  setData(null);
                  setView("dashboard");
                }}
                className="rounded-xl bg-indigo-600 px-3.5 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors shadow-sm"
              >
                Upload new
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        {data ? (
          view === "dashboard" ? (
            <Dashboard data={data} />
          ) : (
            <Chat defaultSessionId={data.session_id} />
          )
        ) : (
          <Upload
            onUploaded={(res) => {
              setData(res);
              setView("dashboard");
            }}
          />
        )}
      </main>
    </div>
  );
}
