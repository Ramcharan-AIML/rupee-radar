// Typed wrappers around the backend API (proxied via Vite: /api -> :8000).

import type { Analysis, UploadResponse } from "../types";

const BASE = "/api";

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Request failed (HTTP ${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) {
        detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      /* non-JSON error body — keep the default message */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export async function uploadStatement(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  return handle<UploadResponse>(res);
}

export async function getAnalysis(sessionId: string): Promise<Analysis> {
  const res = await fetch(`${BASE}/analysis/${sessionId}`);
  return handle<Analysis>(res);
}
