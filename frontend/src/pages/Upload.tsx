import { useRef, useState } from "react";
import { uploadStatement } from "../api/client";
import type { UploadResponse } from "../types";

export default function Upload({ onUploaded }: { onUploaded: (r: UploadResponse) => void }) {
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setBusy(true);
    setError(null);
    try {
      const result = await uploadStatement(file);
      onUploaded(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) void handleFile(file);
  }

  return (
    <div className="mx-auto max-w-2xl py-14 px-4">
      <div className="text-center max-w-md mx-auto mb-10">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700 mb-4">
          🔒 Bank-Grade Privacy
        </span>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Analyze your money
        </h1>
        <p className="mt-3 text-sm text-slate-500 leading-relaxed font-medium">
          Drag &amp; drop your bank statement. We clean, categorize, and formulate advisory insights instantly.
        </p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !busy && inputRef.current?.click()}
        className={`relative overflow-hidden cursor-pointer rounded-3xl border-2 border-dashed p-12 text-center transition-all duration-300 ${
          busy 
            ? "border-indigo-200 bg-indigo-50/10 pointer-events-none" 
            : dragging 
              ? "border-indigo-500 bg-indigo-50/50 scale-[1.01] shadow-lg shadow-indigo-100" 
              : "border-slate-200 bg-white hover:border-indigo-400 hover:shadow-md hover:shadow-slate-100"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.txt,.xlsx,.xls,.pdf"
          className="hidden"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
          }}
        />

        {busy ? (
          <div className="flex flex-col items-center justify-center py-6">
            {/* Pulsing loading spinner */}
            <div className="relative flex items-center justify-center h-16 w-16 mb-4">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-20"></span>
              <span className="relative inline-flex rounded-full h-10 w-10 bg-indigo-600 items-center justify-center text-lg text-white">
                📡
              </span>
            </div>
            <h3 className="text-sm font-semibold text-slate-800">Processing Statement</h3>
            <p className="text-xs text-indigo-600 font-semibold mt-1.5 animate-pulse">
              Parsing schemas &amp; running budget checks...
            </p>
            {/* Fake progress bar skeleton */}
            <div className="w-48 bg-slate-100 h-1.5 rounded-full mt-4 overflow-hidden">
              <div className="bg-indigo-600 h-full rounded-full animate-progress" style={{ width: "65%" }}></div>
            </div>
          </div>
        ) : (
          <div className="space-y-4 py-4">
            <div className="flex justify-center gap-3">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-xl shadow-xs ring-1 ring-emerald-100">
                📊
              </span>
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-xl shadow-xs ring-1 ring-indigo-100">
                📄
              </span>
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-50 text-xl shadow-xs ring-1 ring-amber-100">
                📁
              </span>
            </div>
            
            <div className="space-y-1">
              <p className="text-sm font-bold text-slate-800">
                Drag &amp; drop your statement file here, or <span className="text-indigo-600 underline">browse</span>
              </p>
              <p className="text-xs text-slate-400 font-medium">
                Supports CSV, Excel (XLSX), or PDF bank-statements
              </p>
            </div>

            <div className="pt-4 border-t border-slate-50 flex items-center justify-center gap-6 text-[10px] text-slate-400 uppercase tracking-wider font-bold">
              <span>🔒 100% In-Memory</span>
              <span>•</span>
              <span>🚫 Never Stored</span>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-5 rounded-2xl bg-rose-50 p-4 text-xs text-rose-800 ring-1 ring-rose-200 shadow-sm animate-fade-in flex items-start gap-2.5">
          <span className="text-sm">⚠️</span>
          <div>
            <strong className="font-semibold block mb-0.5">Parse Failure</strong>
            {error}
          </div>
        </div>
      )}
    </div>
  );
}
