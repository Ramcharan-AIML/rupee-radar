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
    <div className="mx-auto max-w-xl py-10">
      <div className="text-center">
        <h1 className="text-2xl font-bold tracking-tight">Upload your bank statement</h1>
        <p className="mt-2 text-sm text-slate-500">
          We’ll clean, categorize, and analyze it locally. CSV files only for now.
        </p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`mt-8 cursor-pointer rounded-2xl border-2 border-dashed p-12 text-center transition ${
          dragging ? "border-indigo-400 bg-indigo-50" : "border-slate-300 bg-white hover:border-indigo-300"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.txt"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
          }}
        />
        {busy ? (
          <p className="text-sm font-medium text-indigo-600">Analyzing…</p>
        ) : (
          <>
            <p className="text-4xl">📄</p>
            <p className="mt-3 text-sm font-medium text-slate-700">
              Drag &amp; drop a CSV here, or click to browse
            </p>
            <p className="mt-1 text-xs text-slate-400">Your data is processed locally.</p>
          </>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700 ring-1 ring-red-200">
          {error}
        </div>
      )}
    </div>
  );
}
