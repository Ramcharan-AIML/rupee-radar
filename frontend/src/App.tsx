import { useState } from "react";
import Upload from "./pages/Upload";
import Dashboard from "./pages/Dashboard";
import type { UploadResponse } from "./types";

export default function App() {
  const [data, setData] = useState<UploadResponse | null>(null);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2">
            <span className="text-xl">📡</span>
            <span className="text-lg font-bold tracking-tight">RupeeRadar</span>
            <span className="hidden text-xs text-slate-400 sm:inline">
              personal finance analyst
            </span>
          </div>
          {data && (
            <button
              onClick={() => setData(null)}
              className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Upload new
            </button>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6">
        {data ? <Dashboard data={data} /> : <Upload onUploaded={setData} />}
      </main>
    </div>
  );
}
