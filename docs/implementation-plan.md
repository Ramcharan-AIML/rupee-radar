# RupeeRadar — Phase-Wise Implementation Plan

> Concrete, sequenced execution plan derived from [architecture.md](architecture.md).
> Each phase lists scope, tasks, files touched, dependencies, acceptance criteria, and a
> demo checkpoint.
>
> **Three bands:**
> - **Foundation (P0–P6):** working app with **zero LLM tokens** — deterministic pipeline + dashboard.
> - **Persistence & cost control (P7–P8):** local storage + token budget/caching, built *before*
>   leaning on the LLM so AI work is cheap and bounded.
> - **Analyst layer (P9–P11):** the LLM "buddy" — fallback categorization, analyst insights +
>   narrative, and chat. Then hardening (P12–P13).
>
> **Token discipline (free tier):** code does all math; the LLM only handles language. Rules +
> permanent cache first, dedup + batch, send *summaries not rows*, cache outputs, hard daily
> budget with graceful degradation. The app stays fully useful even with the LLM off or the
> budget spent. See architecture §0, §13.

**Legend:** 🎯 deliverable · ✅ acceptance criteria · 📦 artifacts/files · ⛓ depends on

---

## Phase 0 — Project Scaffold & Tooling

**Goal:** Runnable empty skeleton for backend + frontend, with config and a health check.

⛓ none

### Tasks
- Initialize git repo; add `.gitignore` (Python, Node, `.env`).
- Create `backend/` with virtualenv, `requirements.txt` (fastapi, uvicorn, pydantic,
  pandas, python-multipart).
- `app/main.py` — FastAPI app, CORS for `localhost:5173`, router registration.
- `app/config.py` — Pydantic `Settings` reading `.env` (LLM provider, key, limits).
- `app/api/routes_health.py` — `GET /api/health` → `{status, llm_provider, llm_enabled}`.
- Create `frontend/` via Vite (React + TypeScript); add Tailwind; verify dev server boots.
- `.env.example` per architecture §8.
- `README.md` with run instructions (backend + frontend).

📦 `backend/app/main.py`, `config.py`, `api/routes_health.py`, `requirements.txt`,
`.env.example`, `frontend/` (Vite scaffold), `.gitignore`, `README.md`

✅ `uvicorn app.main:app` serves `/api/health` returning 200 with provider status.
✅ `npm run dev` serves the React app; CORS allows it to call `/api/health`.

🎯 **Checkpoint:** both servers run; frontend shows backend health status.

---

## Phase 1 — Data Models & Session Store

**Goal:** Canonical Pydantic schemas + in-memory session storage.

⛓ Phase 0

### Tasks
- `app/models/schemas.py` — `Transaction`, `RecurringGroup`, `Metrics`, `Analysis`
  (architecture §3.2), plus `UploadResponse`, `SchemaReport` (detected columns).
- Define `CANONICAL_CATEGORIES` constant (the 10 categories) in one shared module.
- `app/store/session_store.py` — TTL dict keyed by `session_id` (uuid4), with `put/get/purge`
  honoring `SESSION_TTL_MINUTES`. No raw bytes stored — only `Analysis`.

📦 `app/models/schemas.py`, `app/store/session_store.py`, `app/constants.py`

✅ Schemas serialize/deserialize round-trip in a unit test.
✅ Session store returns stored `Analysis` before TTL, `None` after expiry/purge.

🎯 **Checkpoint:** typed contracts ready for the pipeline to fill.

---

## Phase 2 — Ingest & Clean (CSV first)

**Goal:** Turn a messy CSV bank statement into a clean list of `Transaction` objects.

⛓ Phase 1

### Tasks
- **Synthetic test data:** create `tests/sample_statements/messy_sample.csv` mimicking real
  Indian bank statements — UPI/IMPS/NEFT prefixes, ref numbers, `₹`/commas, `Cr/Dr`,
  separate debit/credit columns, opening/closing balance rows, mixed date formats.
- `app/pipeline/ingest.py` — `read_csv` via pandas; **column auto-detection** (fuzzy match
  headers → date / description / amount|debit|credit / balance); emit `SchemaReport`.
- `app/pipeline/clean.py`:
  - Date parsing across common formats → ISO `date`.
  - Amount normalization (strip `₹`, commas, `Cr/Dr`); reconcile debit/credit → `amount` +
    `direction`.
  - `description_clean`: uppercase-fold, strip payment-rail prefixes/ref numbers/trailing IDs.
  - Drop header/balance/duplicate non-transaction rows.

📦 `app/pipeline/ingest.py`, `app/pipeline/clean.py`, `tests/sample_statements/messy_sample.csv`,
`tests/test_clean.py`

✅ Sample CSV parses into N `Transaction`s with correct `date`, `amount`, `direction`.
✅ `description_clean` strips noise (unit-tested on representative messy strings).
✅ Balance/header rows excluded.

🎯 **Checkpoint:** `clean(ingest(file))` → structured transactions (categories empty for now).

---

## Phase 3 — Rule-Based Categorization

**Goal:** Assign each transaction a canonical category deterministically.

⛓ Phase 2

### Tasks
- `app/pipeline/rules.py` — keyword/regex dictionary → category, with confidence
  (e.g. `SWIGGY|ZOMATO|RESTAURANT→Food`, `NETFLIX|HOTSTAR|PRIME→Subscriptions`,
  `EMI|LOAN→EMI`, `RENT→Rent`, `SIP|MUTUAL|ZERODHA→Investments`, `SALARY→Salary`,
  `ELECTRICITY|RECHARGE|BILL→Bills`, `UBER|OLA|IRCTC|FUEL→Travel`, `AMAZON|FLIPKART→Shopping`).
- `app/pipeline/categorize.py` — first pass applies rules; unmatched → `Other`
  (`category_source="default"`). LLM hook is a no-op stub for now (filled Phase 7).

📦 `app/pipeline/rules.py`, `app/pipeline/categorize.py`, `tests/test_categorize.py`

✅ Known merchants in the sample categorize correctly with `category_source="rule"`.
✅ Unknown descriptions fall back to `Other`.
✅ Every category emitted is in `CANONICAL_CATEGORIES`.

🎯 **Checkpoint:** transactions carry categories from rules alone.

---

## Phase 4 — Metrics, Insights & First End-to-End API

**Goal:** Compute financials, generate ≥3 insights, expose the full `/api/upload` pipeline.

⛓ Phase 3

### Tasks
- `app/pipeline/metrics.py` — totals (income/spend), net savings, savings rate, top
  categories, biggest transaction, by-month spend.
- `app/pipeline/insights.py` — template-based, amount-grounded insights (≥3): top category,
  recurring total (placeholder until Phase 6), biggest txn, savings.
- `app/api/routes_upload.py` — `POST /api/upload`: ingest → clean → categorize → metrics →
  insights → build `Analysis`, store in session, return it.
- `app/api/routes_analysis.py` — `GET /api/analysis/{session_id}`.

📦 `app/pipeline/metrics.py`, `insights.py`, `api/routes_upload.py`, `routes_analysis.py`,
`tests/test_metrics.py`, `tests/test_pipeline_e2e.py`

✅ `POST /api/upload` with the sample CSV returns a valid `Analysis` JSON.
✅ Metrics reconcile (income − spend == net_savings); ≥3 insights cite real amounts.
✅ `GET /api/analysis/{id}` returns the stored analysis.

🎯 **Checkpoint:** **backend end-to-end works** (CSV → JSON analysis). Validate via curl/Swagger.

---

## Phase 5 — React Dashboard (MVP UI)

**Goal:** Upload a file and see the analysis rendered.

⛓ Phase 4

### Tasks
- `frontend/src/api/client.ts` — typed fetch wrappers (`uploadStatement`, `getAnalysis`).
- `pages/Upload.tsx` — drag-drop upload + parse feedback (SchemaReport summary).
- `pages/Dashboard.tsx` — orchestrates components from the analysis.
- Components: `SummaryCards` (income/spend/savings/biggest), `CategoryChart` (Recharts
  pie/bar), `InsightsPanel` (≥3 insights), `TransactionTable` (filter/search).
- `lib/format.ts` — ₹ currency + date formatting.

📦 `frontend/src/api/client.ts`, `pages/Upload.tsx`, `pages/Dashboard.tsx`,
`components/{SummaryCards,CategoryChart,InsightsPanel,TransactionTable}.tsx`, `lib/format.ts`

✅ Uploading the sample CSV renders summary cards, category chart, insights, and table.
✅ Currency/dates formatted for Indian locale.

🎯 **Checkpoint:** **full prototype demoable** end-to-end (upload → dashboard). MVP complete.

---

## Phase 6 — Recurring Payment Detection

**Goal:** Detect subscriptions/EMIs/rent/SIPs and surface them.

⛓ Phase 5

### Tasks
- `app/pipeline/recurring.py` — group by normalized merchant; infer cadence from date gaps
  (~7/30/90/365d) + amount stability (low CoV); flag groups with ≥2–3 consistent
  occurrences; tag type from category. Set `is_recurring`/`recurring_group_id` on txns.
- Wire `RecurringGroup`s into `Analysis`; update `insights.py` recurring insight with real
  monthly total.
- Frontend `components/RecurringTable.tsx` + add to Dashboard.

📦 `app/pipeline/recurring.py`, `components/RecurringTable.tsx`, `tests/test_recurring.py`

✅ Repeated monthly merchants in the sample are flagged with correct cadence + typical amount.
✅ One-off transactions are not flagged.
✅ Recurring table renders detected subscriptions/EMIs.

🎯 **Checkpoint:** recurring detection visible in UI; recurring insight uses real numbers.

---

## Phase 7 — Persistent Local Storage (SQLite)

**Goal:** Give the app memory across months and a home for caches — built *before* the LLM so
caching can make AI work cheap. (Architecture §14.)

⛓ Phase 4 (needs `Analysis`); integrate after Phase 6

### Tasks
- `app/store/db.py` — SQLite connection + schema/migrations; `DB_PATH` from config.
- `app/store/repository.py` — persist/load: `analyses`, `transactions`, `recurring_groups`,
  `category_cache`, `insight_cache`, `chat_history`, `llm_usage`.
- Wire `/api/upload` to persist each analysis; replace the in-memory session store with the DB
  (raw file bytes still discarded — only structured results persist).
- `app/api/routes_analysis.py` — add `GET /api/history` (list past analyses).
- Add `data/` to `.gitignore`.

📦 `app/store/db.py`, `app/store/repository.py`, updates to `routes_upload.py`/`routes_analysis.py`,
`tests/test_repository.py`

✅ Upload persists; `GET /api/analysis/{id}` and `GET /api/history` return stored data after restart.
✅ DB file is git-ignored; no raw statement bytes stored.

🎯 **Checkpoint:** analyses survive restarts; history is queryable.

---

## Phase 8 — Token Budget Guard & Cache

**Goal:** Make LLM usage cheap and bounded *before* any LLM feature exists. (Architecture §13.)

⛓ Phase 7

> **Provider limits already captured (since Phase 2):** the Groq free-tier ceilings for
> `llama-3.3-70b-versatile` live in `app/llm/limits.py` — **RPM 30, TPM 1,000, RPD 12,000,
> TPD 100,000**. TPM=1,000 is the binding constraint. `config.py` auto-clamps soft budgets
> inside these. This phase implements the live guard that *enforces* them.

### Tasks
- `app/llm/cache.py` — content-hash cache over the DB (`category_cache`, `insight_cache`):
  get-or-skip helper used by every LLM call site.
- `app/llm/budget.py` — rolling tallies for **all four windows** (RPM/TPM/RPD/TPD) in
  `llm_usage`, seeded from `limits.py`; pre-flight `would_exceed()` across every window +
  the soft `LLM_DAILY_TOKEN_BUDGET`; **pacing/queueing** to respect TPM=1,000 (keep calls
  small and spaced, don't burst); post-call token accounting; 429 + `Retry-After` back-off.
- `app/api/routes_usage.py` — `GET /api/usage` → `{used, remaining, provider, degraded,
  per_minute, per_day}`.
- Config: limits + budgets + feature toggles (architecture §8) — already defined.
- Frontend `components/BudgetBadge.tsx` consuming `/api/usage`.

📦 `app/llm/cache.py`, `app/llm/budget.py`, `api/routes_usage.py`, `components/BudgetBadge.tsx`,
`tests/test_budget.py`, `tests/test_cache.py`

✅ Cache hit returns without any provider call.
✅ A call projected to breach **any** window (RPM/TPM/RPD/TPD or the soft daily budget) is
   skipped; the guard reports `degraded` and callers fall back to baseline (no call made).
✅ TPM pacing keeps per-minute token use ≤ 1,000; no 429 from bursting under normal load.
✅ Usage tallies persist and reset on their windows; `/api/usage` reflects them.

🎯 **Checkpoint:** cost-control rails exist; AI can now be added safely.

---

## Phase 9 — LLM Fallback Categorization (token-frugal)

**Goal:** Categorize messy/unknown descriptions via `llama-3.3-70b-versatile`, rules-first,
deduped, batched, cached, behind the provider interface. (Architecture §12 role 1.)

⛓ Phase 3 (logic), Phase 8 (budget+cache)

### Tasks
- `app/llm/provider.py` — `LLMProvider` protocol (`classify`/`complete`/`chat`).
- `app/llm/groq_provider.py` — OpenAI-compatible client → Groq; strict JSON prompt, low temp.
- `app/llm/ollama_provider.py` — local, unlimited fallback (same interface).
- `app/llm/factory.py` — select provider from `LLM_PROVIDER` (`groq`/`ollama`/`none`).
- `categorize.py` second pass: collect `Other`/low-confidence txns → **dedup** by
  `description_clean` → check `category_cache` → **batch** remaining (`LLM_CATEGORIZE_BATCH`)
  through `budget` guard → write results to cache; set `category_source="llm"`. Map any
  out-of-vocab category to `Other`. Graceful degrade to rules if disabled/over-budget/errored.

📦 `app/llm/{provider,groq_provider,ollama_provider,factory}.py`, updates to `categorize.py`,
`tests/test_categorize_llm.py` (mocked provider)

✅ `LLM_PROVIDER=none` → identical to Phase 3, zero network calls.
✅ Unknown messy descriptions get sensible categories (`category_source="llm"`); only cleaned
   strings sent; every output ∈ `CANONICAL_CATEGORIES`.
✅ Duplicate descriptions → one call (dedup + cache); repeats across uploads → zero calls.
✅ Provider error / over-budget → falls back to rules without failing the request.

🎯 **Checkpoint:** AI categorization improves accuracy at near-zero ongoing token cost.

---

## Phase 10 — Analyst Insights & Monthly Narrative (LLM, summaries only)

**Goal:** Turn metrics into specific, advisory insights + a written monthly briefing — over a
**compact numeric summary**, never raw transactions. (Architecture §12 roles 2–3.)

⛓ Phase 8 (budget+cache), Phase 6 (recurring for richer summary)

### Tasks
- `app/pipeline/summary.py` — build the compact summary (totals, category shares, recurring
  list, biggest txns, month deltas) — the only thing sent to the LLM.
- `app/analyst/insights.py` — template baseline always; `LLM_INSIGHT_MODE` adds `polish`
  (rephrase) or `generate` (analytical insights: anomalies, savings tips). Cached per analysis.
- `app/analyst/narrative.py` — one short LLM call → monthly narrative; cached in `insight_cache`.
- Frontend `components/NarrativePanel.tsx`; upgrade `InsightsPanel` for advisory insights.

📦 `app/pipeline/summary.py`, `app/analyst/{insights,narrative}.py`, frontend panels,
`tests/test_summary.py`, `tests/test_insights_llm.py` (mocked)

✅ Insights/narrative cite only code-computed numbers (no LLM arithmetic).
✅ Re-running the same analysis hits the cache (no new tokens).
✅ With LLM off/over-budget, template insights still render (≥3); narrative omitted cleanly.

🎯 **Checkpoint:** insights read like an analyst's notes; tokens spent once per analysis.

---

## Phase 11 — Conversational Chat ("Ask your money anything")

**Goal:** Chat grounded in computed data via **tool-use** (no context-stuffing). Most
token-hungry feature → independently toggleable + history-capped. (Architecture §12 role 4.)

⛓ Phase 9 + Phase 10

### Tasks
- `app/analyst/tools.py` — callable tools over computed data: `get_metrics`,
  `get_category_breakdown`, `get_recurring`, `get_top_transactions`, `compare_months`,
  `search_transactions`.
- `app/analyst/chat.py` — orchestrate provider `chat()` with tool schemas; run tools in code;
  return `{answer, used_tools, tokens_spent}`. Cap history to last N turns; route through budget.
- `app/api/routes_chat.py` — `POST /api/chat`. Persist turns to `chat_history`.
- Frontend `pages/Chat.tsx` + `components/ChatPanel.tsx`.

📦 `app/analyst/{tools,chat}.py`, `api/routes_chat.py`, `pages/Chat.tsx`,
`components/ChatPanel.tsx`, `tests/test_chat_tools.py` (mocked)

✅ Numeric answers come from tool results (code), not model arithmetic.
✅ Full transaction list is never sent to the model.
✅ `LLM_ENABLE_CHAT=false` or over-budget → endpoint returns a graceful "chat unavailable".
✅ History capped; tokens per question bounded.

🎯 **Checkpoint:** the "analyst buddy" answers real questions about your money.

---

## Phase 12 — Report Export (HTML → PDF/CSV)

**Goal:** Downloadable, shareable report including the narrative.

⛓ Phase 10 (narrative content)

### Tasks
- `app/report/generator.py` — Jinja2 HTML (summary, category chart/table, recurring, insights,
  **narrative**); render to PDF (WeasyPrint/pdfkit); CSV export of transactions via pandas.
- `app/api/routes_report.py` — `GET /api/report/{id}?format=pdf|csv|html`.
- Frontend download buttons.

📦 `app/report/generator.py`, `api/routes_report.py`, report template, frontend download UI

✅ Each format downloads with summary, categories, recurring, insights, narrative.
✅ CSV matches cleaned/categorized transactions.

🎯 **Checkpoint:** shareable report deliverable complete.

---

## Phase 13 — Robustness, Extra Formats & Hardening

**Goal:** Handle more real-world inputs and finalize quality.

⛓ Phase 12

### Tasks
- `ingest.py`: XLSX (`openpyxl`) and best-effort PDF (`pdfplumber`) parsing.
- Upload validation: size limit (`MAX_UPLOAD_MB`), type checks, friendly parse-failure errors.
- Expand rule dictionary; add 2–3 more synthetic bank-format samples.
- Edge cases per [edge-cases.md](edge-cases.md): empty/no-credit/single-month/unparseable.
- Test pass (pytest) incl. mocked LLM; frontend empty/error/degraded states.
- Update `README.md` (run, configure, token budget, privacy); finalize `.env.example`.

📦 updates to `ingest.py`, `routes_upload.py`, `rules.py`, more `tests/sample_statements/*`,
expanded test suite, `README.md`

✅ XLSX and a sample PDF parse end-to-end.
✅ Invalid/oversized uploads return clear errors, not 500s.
✅ Test suite green; setup verified from scratch.

🎯 **Checkpoint:** robust, documented, personal-analyst app ready for daily use.

---

## Dependency Flow

```
Foundation (zero tokens):
  P0 ─► P1 ─► P2 ─► P3 ─► P4 ─► P5 ─► P6

Persistence & cost control:
  P4 ─► P7 (storage) ─► P8 (budget + cache)

Analyst layer (LLM, frugal):
  P3,P8 ─► P9 (categorization)
  P6,P8 ─► P10 (insights + narrative)
  P9,P10 ─► P11 (chat)

Hardening:
  P10 ─► P12 (report) ─► P13 (formats + polish)
```

- **MVP (zero tokens):** P0–P6 — working end-to-end app, no LLM needed.
- **Cheap AI rails:** + P7–P8 — storage, caching, budget guard.
- **Analyst brain:** + P9–P11 — fallback categorization, insights/narrative, chat.
- **Polish:** + P12–P13 — report, extra formats, hardening.

---

## Requirement → Phase Traceability

| Core requirement (context §2) | Phase(s) |
|---|---|
| 1. Accept statement input | P2 (CSV), P13 (XLSX/PDF) |
| 2. Extract/clean → structured | P2 |
| 3. Categorize (10 categories) | P3 (rules), P9 (LLM fallback) |
| 4. Detect recurring | P6 |
| 5. Key metrics | P4 |
| 6. Human-readable insights (≥3) | P4 (template), P10 (LLM analyst + narrative) |
| 7. UI / dashboard / report | P5 (dashboard), P12 (report) |
| Privacy-conscious handling | P7 (local DB, no raw bytes), P8/P9/P10 (summaries-only to LLM) |
| **Personal analyst (added)** | P7 (history), P10 (insights/narrative), P11 (chat) |
| **Token/cost discipline (added)** | P8 (budget+cache), threaded through P9–P11 |

---

## Suggested Milestones

| Milestone | Phases | Outcome |
|---|---|---|
| **M1 — Backend pipeline** | P0–P4 | CSV → analysis JSON via API |
| **M2 — Demoable MVP** | + P5, P6 | Upload → dashboard + recurring (zero tokens) |
| **M3 — Cheap-AI ready** | + P7, P8 | History, caching, token budget guard in place |
| **M4 — Analyst buddy** | + P9, P10, P11 | LLM categorization, insights/narrative, chat |
| **M5 — Daily driver** | + P12, P13 | Report, multi-format, hardened, documented |
