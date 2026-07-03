# RupeeRadar

AI-powered **personal finance analyst** that turns messy bank statement data into clean,
categorized, human-readable spending insights — with an LLM "analyst buddy" layer on top of a
deterministic, number-accurate pipeline.

> **Design docs:** [context](docs/context.md) · [architecture](docs/architecture.md) ·
> [implementation plan](docs/implementation-plan.md) · [edge cases](docs/edge-cases.md)

## Status

**Phase 0 — Project scaffold complete.** Runnable backend (FastAPI) + frontend (Vite/React/
Tailwind) skeleton with config and a health check. The data pipeline, dashboard, and AI
features arrive in later phases (see the implementation plan).

## Stack

- **Backend:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2
- **Frontend:** React + Vite + TypeScript + Tailwind CSS
- **LLM (later phases):** Groq `llama-3.3-70b-versatile` (free tier) — optional, with an
  Ollama local alternative. Code does all the math; the LLM only handles language.

## Prerequisites

- Python 3.11+ and pip
- Node.js 18+ and npm

## Setup & Run

### 1. Backend (`http://localhost:8000`)

```bash
cd backend
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # then edit .env (set GROQ_API_KEY for AI features)

uvicorn app.main:app --reload
```

Check it:
- Health: http://localhost:8000/api/health
- Interactive API docs: http://localhost:8000/docs

### 2. Frontend (`http://localhost:5173`)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — it calls the backend (via the `/api` proxy) and shows the
backend health + LLM provider status.

## Configuration

All backend settings live in `backend/.env` (see `backend/.env.example`). Key ones:

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `groq` (default), `ollama`, or `none` |
| `GROQ_API_KEY` | required when `LLM_PROVIDER=groq` (free at console.groq.com) |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` |
| `LLM_DAILY_TOKEN_BUDGET` | hard daily token cap; AI degrades to baseline beyond it |
| `DB_PATH` | local SQLite path (later phases) |
| `MAX_UPLOAD_MB` | upload size limit |

Without a `GROQ_API_KEY`, the app still runs — AI features simply report as disabled
(`llm_enabled: false`) and later phases fall back to rules-only.

## Privacy

Local-first: processing and storage stay on your machine. AI calls (when enabled) send only
cleaned merchant text / compact numeric summaries — never account numbers, balances, or names.
`.env` and `data/` are git-ignored.
