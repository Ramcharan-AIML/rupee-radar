# RupeeRadar — Architecture

> AI-powered **personal finance analyst** that converts messy bank statement data into clean,
> categorized insights — with an LLM "analyst buddy" layer (insights, narrative reports, and
> chat) sitting on top of a deterministic, number-accurate pipeline.
>
> Source of truth for requirements: [context.md](context.md) · [problemStatement.txt](problemStatement.txt)

---

## 0. Guiding Principles

1. **Code does the math; the LLM does the language.** Every rupee figure is computed
   deterministically in Python. The LLM only *explains, advises, and converses* over numbers
   already computed — it never sums, counts, or calculates. This is what keeps a "finance
   analyst" trustworthy. (See §0a.)
2. **The LLM is the brain, but tokens are scarce.** We run on Groq's **free tier**, so every
   design choice minimizes token spend: rules-first, permanent caching, dedup, batching, and
   sending *summaries not raw transactions*. The app must stay fully useful even after the
   daily token budget is exhausted. (See §13.)
3. **Local-first & private.** Runs on the user's machine; data persists locally (SQLite); only
   compact, de-identified summaries ever reach the LLM. (See §7, §14.)
4. **Graceful degradation.** No LLM key, rate-limited, budget exhausted, or offline → the app
   still categorizes (rules + cache), computes metrics, and shows insights. AI features
   light up when available.

### 0a. The "LLM does not do math" boundary

```
            ┌─────────────────────────── DETERMINISTIC (Python) ───────────────────────────┐
 raw file ─►│ ingest → clean → categorize(rules+cache) → recurring → metrics(all numbers)   │
            └───────────────────────────────────┬──────────────────────────────────────────┘
                                                 │  compact numeric summary (few hundred tokens)
                                                 ▼
            ┌──────────────────────────── LLM LAYER (language only) ──────────────────────┐
            │  category fallback (unknowns) · analyst insights · narrative report · chat   │
            └─────────────────────────────────────────────────────────────────────────────┘
```

The LLM receives *"Food = ₹12,400 (28%), +40% vs last month"* — it never receives 300 rows to
add up. Every number it speaks was computed by code.

---

## 1. Decisions (locked)

| Area | Choice | Rationale |
|---|---|---|
| **Stack** | **Python (FastAPI) backend + React frontend** | Clean API/UI separation; polished dashboard + chat; Python keeps the data pipeline simple. |
| **Categorization** | **Rules-first + permanent cache + LLM fallback** | Rules/cache handle the bulk for **zero tokens**; LLM only classifies genuinely-unknown descriptions, batched & deduped. |
| **LLM role** | **Core analyst layer** (categorization fallback, insights, narrative report, chat) — *language only, never math* | Turns the app from a dashboard into a personal finance buddy, while numbers stay code-computed and trustworthy. |
| **LLM model** | **`llama-3.3-70b-versatile` via Groq** (free) · **Ollama** local alternative | Free, fast, strong enough. Ollama = unlimited/offline escape hatch behind the same interface. |
| **Token policy** | **Hard budgets + caching + summaries-not-rows** | Free tier has RPM/TPM/RPD limits; design must never blow through them and must degrade cleanly. (§13) |
| **Storage** | **Local SQLite** (history, caches, usage log) | Personal daily-driver needs month-over-month history; caches make repeat LLM work free. (§14) |
| **Data residency** | **Local-only** | All parsing/processing/storage on the user's machine; only compact de-identified summaries leave (if LLM enabled). |
| **Privacy posture** | De-identified LLM payloads; local DB; secrets in `.env` | Personal data stays with the user. |

### On the LLM choice
- `llama-3.3-70b-versatile` is served free by **Groq** (OpenAI-compatible API). Good fit for
  short classification prompts, structured insights, and chat; batchable; low latency.
- **Free-tier reality:** Groq enforces requests-per-minute, tokens-per-minute, and
  requests-per-day limits. We treat tokens as a **budget to spend wisely**, not an unlimited
  resource — see §13 for the full cost-control strategy.
- **Privacy + token trade-off:** using a cloud LLM means *some* text leaves the machine.
  Mitigations (also save tokens):
  - Send only **cleaned merchant strings** (categorization) or **compact numeric summaries**
    (insights/chat) — never account numbers, balances, or full statement rows.
  - LLM categorization is a **fallback**, invoked only for what rules + cache can't resolve.
  - **Cache everything** keyed by content hash so the same work is never paid for twice.
  - **Fully-local alternative:** set `LLM_PROVIDER=ollama` (`llama3.3`) behind the same
    interface — zero code change above the provider boundary, and **no token limits at all**.
    See §9.

---

## 2. System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                          React Frontend (SPA)                          │
│  Upload · Dashboard (charts) · Recurring view · Insights · Report DL   │
└───────────────┬───────────────────────────────────────────────────────┘
                │  HTTP / JSON (REST)
                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend (local)                        │
│                                                                        │
│   /upload ─► Ingest ─► Clean ─► Categorize ─► Recurring ─► Metrics     │
│                                     │                                   │
│                                     ▼ (fallback, optional)             │
│                            LLM Provider (Groq / Ollama)               │
│                                                                        │
│   /report ─► Report Generator (HTML/PDF/CSV)                          │
└───────────────┬───────────────────────────────────────────────────────┘
                │
                ▼
        In-memory session store (no raw data persisted by default)
```

**Flow:** user uploads a statement → backend runs the pipeline → returns a structured
analysis JSON → React renders dashboard + insights → user downloads a shareable report.

---

## 3. Backend Architecture (FastAPI)

### 3.1 Module layout

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, router registration
│   ├── config.py               # Settings (env): LLM provider, key, token budgets, limits
│   ├── api/
│   │   ├── routes_upload.py     # POST /api/upload  -> analyze pipeline
│   │   ├── routes_analysis.py   # GET  /api/analysis/{id}, GET /api/history
│   │   ├── routes_report.py     # GET  /api/report/{id}?format=pdf|csv|html
│   │   ├── routes_chat.py       # POST /api/chat  -> analyst Q&A (tool-use)
│   │   └── routes_usage.py      # GET  /api/usage -> token budget status
│   ├── pipeline/
│   │   ├── ingest.py            # [1] parse CSV/XLSX/PDF -> raw rows
│   │   ├── clean.py             # [2] normalize dates/amounts, clean descriptions
│   │   ├── categorize.py        # [3] rules-first + cache + LLM fallback orchestration
│   │   ├── rules.py             # keyword/regex -> category dictionary
│   │   ├── recurring.py         # [4] recurring/subscription/EMI detection
│   │   ├── metrics.py           # [5] totals, savings, top categories, biggest txn
│   │   └── summary.py           # builds the COMPACT numeric summary sent to the LLM
│   ├── analyst/                 # LLM "analyst buddy" layer (language only)
│   │   ├── insights.py          # [6] insights: template baseline + optional LLM polish
│   │   ├── narrative.py         # monthly narrative report (over summary, cached)
│   │   ├── chat.py              # conversational Q&A via tool-use over computed data
│   │   └── tools.py             # callable "tools": query metrics/txns/recurring
│   ├── llm/
│   │   ├── provider.py          # abstract LLMProvider interface (classify/complete/chat)
│   │   ├── groq_provider.py     # llama-3.3-70b-versatile via Groq
│   │   ├── ollama_provider.py   # local, unlimited fallback (optional)
│   │   ├── factory.py           # selects provider from LLM_PROVIDER
│   │   ├── budget.py            # token budget guard + usage tracking
│   │   └── cache.py             # content-hash cache (categories, insights, narrative)
│   ├── models/
│   │   └── schemas.py           # Pydantic models (Transaction, Analysis, ChatTurn, etc.)
│   ├── report/
│   │   └── generator.py         # HTML -> PDF/CSV export
│   └── store/
│       ├── db.py                # SQLite connection + schema/migrations
│       └── repository.py        # persist/load analyses, caches, usage, chat history
├── data/
│   └── rupeeradar.db            # local SQLite (gitignored) — history + caches + usage
├── tests/
│   └── sample_statements/       # synthetic messy statements for testing
├── requirements.txt
└── .env.example                 # GROQ_API_KEY, LLM_PROVIDER, token budgets, etc.
```

### 3.2 Core data model (Pydantic)

```python
class Transaction(BaseModel):
    id: str
    date: date
    description_raw: str            # original messy text
    description_clean: str          # normalized merchant/text
    amount: float                   # absolute value
    direction: Literal["debit", "credit"]
    category: str                   # one of the 10 canonical categories
    category_source: Literal["rule", "llm", "default"]
    confidence: float               # 0..1
    is_recurring: bool = False
    recurring_group_id: str | None = None

class RecurringGroup(BaseModel):
    id: str
    merchant: str
    cadence: Literal["weekly", "monthly", "quarterly", "yearly", "irregular"]
    typical_amount: float
    occurrences: int
    category: str                   # e.g. Subscriptions, EMI, Rent

class Metrics(BaseModel):
    total_income: float
    total_spend: float
    net_savings: float
    savings_rate: float             # net_savings / total_income
    top_categories: list[tuple[str, float]]
    biggest_transaction: Transaction
    by_month: dict[str, float]      # month -> spend

class Analysis(BaseModel):
    session_id: str
    transactions: list[Transaction]
    recurring: list[RecurringGroup]
    metrics: Metrics
    insights: list[str]             # >= 3 human-readable insights
```

---

## 4. Processing Pipeline (the 6 stages)

### [1] Ingest & parse — `ingest.py`
- **Inputs:** CSV (primary), XLSX, PDF (best-effort).
  - CSV/XLSX → `pandas.read_csv` / `read_excel`.
  - PDF → `pdfplumber` table extraction (best-effort, per the "don't perfect every format"
    constraint).
- **Column auto-detection:** fuzzy-match headers to canonical fields
  (`date`, `description`/`narration`/`particulars`, `amount`/`debit`/`credit`, `balance`).
- **Output:** list of raw row dicts + a detected-schema report (for the UI to show what was
  parsed).

### [2] Clean & normalize — `clean.py`
- Parse dates across common formats → ISO `date`.
- Normalize amounts: strip `₹`, commas, `Cr/Dr` suffixes; resolve sign → `direction`.
- Reconcile separate debit/credit columns into `amount` + `direction`.
- **Description cleaning:** uppercase-fold, strip UPI/IMPS/NEFT prefixes, reference numbers,
  trailing IDs, and bank noise → `description_clean` (this is the *only* text sent to the LLM).
- Drop duplicate/non-transaction rows (headers, opening/closing balance lines).

### [3] Categorize — `categorize.py` + `rules.py`
Two-tier strategy:
1. **Rule engine (first pass):** keyword/regex dictionary maps cleaned descriptions to
   categories (e.g. `SWIGGY|ZOMATO|RESTAURANT → Food`, `NETFLIX|PRIME|HOTSTAR →
   Subscriptions`, `EMI|LOAN → EMI`, `SALARY|CREDIT.*NEFT → Salary`). High confidence.
2. **LLM fallback (second pass):** transactions left as `Other` or low-confidence are
   **batched** (e.g. 20–50 per request) and sent to `llama-3.3-70b-versatile` with a strict
   prompt: *"Classify each description into exactly one of [10 categories]; return JSON."*
   - Deterministic output enforced via JSON schema / low temperature.
   - Results cached by `description_clean` to avoid re-calling for repeats.
3. **Default:** if LLM disabled/unavailable → stays `Other` (`category_source="default"`).

Canonical categories: `Food · Travel · Shopping · Bills · EMI · Subscriptions · Salary ·
Rent · Investments · Other`.

### [4] Recurring detection — `recurring.py`
- Group transactions by **normalized merchant** (`description_clean` key).
- For each group, detect cadence from **date gaps** (≈30d → monthly, ≈7d → weekly, etc.)
  and **amount stability** (low coefficient of variation).
- Flag as recurring if ≥ 2–3 occurrences with consistent cadence/amount.
- Tag type from category (Subscriptions, EMI, Rent, Investments→SIP, Bills→insurance).

### [5] Metrics — `metrics.py`
- `total_income` = Σ credits; `total_spend` = Σ debits.
- `net_savings` = income − spend; `savings_rate`.
- `top_categories` = spend grouped by category, sorted desc.
- `biggest_transaction`; `by_month` spend trend.

### [6] Insights — `insights.py`
- **≥ 3** human-readable insights using **actual amounts**, e.g.:
  - "Food was your biggest category at ₹X (Y% of spend)."
  - "You have N recurring payments totaling ₹Z/month."
  - "Your biggest single transaction was ₹A to <merchant> on <date>."
  - "You saved ₹S this period (R% of income)."
- Generated from `Metrics`/`RecurringGroup` via templates (deterministic). Optional LLM
  polish pass to make phrasing more natural — still grounded in computed numbers.

---

## 5. API Surface

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/upload` | Multipart file upload → runs full pipeline → persists + returns `Analysis` + `id`. |
| `GET` | `/api/analysis/{id}` | Re-fetch a stored analysis. |
| `GET` | `/api/history` | List past analyses (month-over-month) from local DB. |
| `GET` | `/api/report/{id}?format=pdf\|csv\|html` | Download shareable report (narrative incl.). |
| `POST` | `/api/chat` | Analyst Q&A: `{id, message, history}` → grounded answer via tool-use. |
| `GET` | `/api/usage` | Token budget status (used/remaining today, provider, degraded?). |
| `GET` | `/api/health` | Liveness + LLM-provider status (enabled/disabled/budget-exhausted). |

**Response shape** = the `Analysis` model (§3.2) serialized to JSON. Chat returns
`{answer, used_tools, tokens_spent}`. All LLM-backed endpoints **degrade gracefully** when
the LLM is disabled or the budget is exhausted (return the deterministic baseline + a flag).

---

## 6. Frontend Architecture (React)

```
frontend/src/
├── api/client.ts            # fetch wrappers for the API
├── pages/
│   ├── Upload.tsx           # drag-drop upload + parse feedback
│   └── Dashboard.tsx        # main results view
├── components/
│   ├── SummaryCards.tsx     # income / spend / savings / biggest txn
│   ├── CategoryChart.tsx    # pie/bar of spend by category
│   ├── TrendChart.tsx       # monthly spend line chart
│   ├── RecurringTable.tsx   # detected subscriptions/EMIs
│   ├── InsightsPanel.tsx    # the >= 3 insights
│   └── TransactionTable.tsx # cleaned + categorized txns (filter/search)
└── lib/format.ts            # ₹ currency / date formatting
```

Additional analyst components:
- `pages/Chat.tsx` + `components/ChatPanel.tsx` — "Ask your money anything" conversation.
- `components/NarrativePanel.tsx` — the monthly written briefing.
- `components/HistoryView.tsx` — month-over-month list/trend from `/api/history`.
- `components/BudgetBadge.tsx` — small token-budget indicator (uses `/api/usage`); shows when
  AI is running on rules-only because the budget is spent.

- **Charts:** Recharts (or Chart.js). **State:** lightweight (React Query). **Styling:**
  Tailwind. **Report download** triggers `/api/report`. **Chat** streams/awaits `/api/chat`.

---

## 7. Privacy & Security

- **Local-only:** backend runs on `localhost`; SQLite DB lives in `data/` on the user's machine.
- **Local persistence (personal tool):** analyses, caches, usage log, and chat history are
  stored in **local SQLite** so the app can compare months and reuse cached LLM work. Raw
  uploaded file bytes are still **discarded after parsing** — only structured results persist.
  The DB file is **git-ignored**. (See §14.)
- **Minimal LLM exposure:** categorization sends only `description_clean` strings; insights,
  narrative, and chat send only **compact numeric summaries** (totals, category shares,
  recurring list, month deltas) — never account numbers, balances, or counterparty names.
- **Secrets:** API key via `.env` (git-ignored); never hard-coded or logged. LLM usage logs
  store token counts only, never prompt contents with PII.
- **Fully-local mode:** set `LLM_PROVIDER=ollama` for AI features with **zero data egress and
  no token limits**, or `none` to disable AI entirely.

---

## 8. Configuration (`.env`)

```ini
# --- Provider ---
LLM_PROVIDER=groq               # groq | ollama | none
GROQ_API_KEY=...                # required only if LLM_PROVIDER=groq
GROQ_MODEL=llama-3.3-70b-versatile
OLLAMA_MODEL=llama3.3           # used if LLM_PROVIDER=ollama

# --- Token budget / cost control (free-tier guard, see §13) ---
LLM_DAILY_TOKEN_BUDGET=200000   # hard cap/day; beyond it, AI features degrade to baseline
LLM_MAX_TOKENS_PER_CALL=800     # cap on completion size (insights/chat are short)
LLM_CATEGORIZE_BATCH=40         # unknown descriptions per classification request
LLM_ENABLE_CHAT=true            # chat is the most token-hungry feature; toggle independently
LLM_ENABLE_NARRATIVE=true       # monthly narrative report via LLM
LLM_INSIGHT_MODE=polish         # off | polish (LLM rephrases template insights) | generate

# --- Storage & limits ---
DB_PATH=./data/rupeeradar.db
MAX_UPLOAD_MB=10
```

---

## 9. LLM Provider Abstraction

A single interface keeps the analyst layer independent of the provider:

```python
class LLMProvider(Protocol):
    def classify(self, descriptions: list[str], categories: list[str]) -> list[str]: ...
    def complete(self, system: str, user: str, max_tokens: int) -> str: ...   # insights/narrative
    def chat(self, messages: list[dict], tools: list[dict] | None) -> ChatResult: ...

# groq_provider.py  -> OpenAI-compatible client pointed at Groq, model from env
# ollama_provider.py -> local Ollama HTTP API (unlimited, offline)
# none               -> no-op: classify -> "Other"; complete/chat -> deterministic baseline
```

Every call routes through `budget.py` (pre-flight token estimate + post-call accounting) and
`cache.py` (skip the call entirely on a cache hit). Swapping `LLM_PROVIDER` changes nothing
above this boundary.

---

## 10. Tech Stack Summary

| Layer | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Data | pandas, pdfplumber (PDF), openpyxl (XLSX) |
| Storage | SQLite (stdlib `sqlite3` / SQLModel) — local history, caches, usage log |
| LLM | Groq (`llama-3.3-70b-versatile`) via OpenAI-compatible client; Ollama optional |
| Validation | Pydantic v2 |
| Frontend | React + Vite + TypeScript, Recharts, Tailwind |
| Report | Jinja2 (HTML) → WeasyPrint/pdfkit (PDF), pandas (CSV) |
| Testing | pytest + synthetic messy statements + mocked LLM |

---

## 11. Build Order (suggested)

**Foundation (deterministic, no/low tokens):**
1. Scaffold FastAPI app + Pydantic schemas + `/health`.
2. Ingest + clean (CSV first) with a synthetic messy sample.
3. Rule-based categorizer + canonical categories.
4. Metrics + template insights → first end-to-end JSON via `/api/upload`.
5. React dashboard: summary cards + category chart + transaction table.
6. Recurring detection + recurring table.

**Persistence & cost control (build before leaning on the LLM):**
7. SQLite storage + repository (history, caches, usage log).
8. Token budget guard + content-hash cache + usage endpoint/badge.

**Analyst layer (LLM, token-frugal):**
9. LLM fallback categorization (rules-first, deduped, batched, cached).
10. LLM analyst insights + monthly narrative (over compact summary, cached).
11. Conversational chat with tool-use over computed data.

**Hardening:**
12. Report export (HTML → PDF/CSV, includes narrative).
13. XLSX/PDF ingest (best-effort), polish, tests.

> Steps 1–6 are a fully working app with **zero tokens**. Steps 7–8 make AI work cheap and
> bounded. Steps 9–11 add the analyst brain. The app stays useful at every step even if the
> LLM is off or the budget is spent.

---

## 12. LLM Intelligence Layer (Personal Analyst)

Four roles, ordered cheapest → most expensive. All **language-only** (§0a); none compute numbers.

| Role | What it does | Token strategy |
|---|---|---|
| **1. Category fallback** | Classify descriptions rules+cache couldn't | Rules-first; only unknowns; deduped; batched (`LLM_CATEGORIZE_BATCH`); result cached **forever** per description. Most uploads cost ~0 after warm-up. |
| **2. Analyst insights** | Turn metrics into specific, advisory insights (anomalies, savings tips) | Input = compact summary (~few hundred tokens), not transactions. Cached per analysis; regenerated only if data changes. `LLM_INSIGHT_MODE` lets you keep template insights and only *polish* wording. |
| **3. Monthly narrative** | A written briefing of the month | One short call over the summary; cached per analysis; `max_tokens` capped. |
| **4. Chat (Ask your money anything)** | Conversational Q&A | **Tool-use**, not context-stuffing — see below. Most token-hungry, so it's independently toggleable (`LLM_ENABLE_CHAT`) and history-capped. |

### Chat via tool-use (not context-stuffing)
We never paste all transactions into the prompt. The LLM is given a small set of **tools**
(`analyst/tools.py`) it can call against already-computed data:

```
get_metrics()                      get_category_breakdown(month?)
get_recurring()                    get_top_transactions(n, category?, month?)
compare_months(a, b)               search_transactions(query, month?)
```

Flow: user asks → model picks a tool → backend runs it (deterministic, in code) → model gets
small structured results → model answers in words. Numbers come from code; phrasing from the
LLM. Conversation history is capped (e.g. last N turns) to bound tokens.

---

## 13. Token Budget & Cost Control (free-tier guard)

**Groq free-tier limits for `llama-3.3-70b-versatile` (the ceilings we must respect):**

| Window | Limit | Notes |
|---|---|---|
| Requests / minute (RPM) | **30** | |
| Tokens / minute (TPM) | **1,000** | **binding constraint** — dictates how small each call must be |
| Requests / day (RPD) | **12,000** | |
| Tokens / day (TPD) | **100,000** | the daily token budget can't exceed this |

The **1,000 TPM** ceiling is the one that shapes the design: a single request (prompt + input
+ completion) must stay well under 1,000 tokens, and we can make at most ~1,000 tokens' worth
of calls per minute. Defaults are set accordingly — `LLM_MAX_TOKENS_PER_CALL=500`,
`LLM_CATEGORIZE_BATCH=15`, `LLM_DAILY_TOKEN_BUDGET=100,000` — and `config.py` auto-clamps any
soft setting back inside these hard ceilings. The limits live in one place: `app/llm/limits.py`.

The app must be **frugal by construction** and **degrade cleanly** when limits hit — never
break, never hang.

**Spend-reduction tactics (in priority order):**
1. **Rules + permanent cache first** — categorization is mostly free after warm-up; a repeat
   description is never re-sent.
2. **Dedup before sending** — N identical descriptions → 1 classification.
3. **Batch** — many unknowns in one request (`LLM_CATEGORIZE_BATCH`).
4. **Summaries, not rows** — insights/narrative/chat see compact aggregates, not transactions.
5. **Cache outputs** — insights & narrative cached per analysis (content hash); chat answers
   cacheable per (analysis, question).
6. **Cap sizes** — `LLM_MAX_TOKENS_PER_CALL`; short prompts; low temperature.
7. **Feature toggles** — turn off the expensive bits (`LLM_ENABLE_CHAT`, `INSIGHT_MODE=off`)
   independently when you want to conserve.

**Hard guard (`llm/budget.py`) — enforces all four windows:**
- Maintains rolling tallies for **RPM, TPM, RPD, TPD** (minute + day counters persisted in
  SQLite `llm_usage`), seeded from `app/llm/limits.py`.
- **Pre-flight:** estimate a call's tokens; if it would breach *any* window (per-minute or
  per-day, requests or tokens) — including the soft `LLM_DAILY_TOKEN_BUDGET` — skip the LLM
  and return the deterministic baseline with a `degraded=true` flag.
- **Pacing:** because TPM is only 1,000, the guard paces/queues calls within the minute window
  (and keeps each call small) rather than firing a burst that would 429.
- **Rate-limit handling:** on Groq 429, respect `Retry-After`, back off, and fall back to
  baseline for that request — never hang.
- **Post-call:** record actual tokens used; expose remaining headroom via `/api/usage` +
  `BudgetBadge`.

**Budget math under these limits (typical month, ~300 txns):**
- Categorization: most hit rules/cache. ~30 unknowns → batches of 15 ≈ 2 calls, each a few
  hundred tokens → well under TPM, and free thereafter via cache.
- Insights + narrative: ~2 short calls (≤500-token completions), cached per analysis.
- Chat: ~300–500 tokens per question, history-capped.
→ A full monthly analysis costs a few thousand tokens — comfortably inside 100k/day. The
binding limit in practice is **TPM (1,000)**, which the pacing guard handles by keeping calls
small and spaced. **Ollama removes all ceilings** when you want unlimited/offline use.

---

## 14. Persistent Local Storage (SQLite)

A personal daily-driver needs memory across months and a place to cache LLM work.

**Tables (conceptual):**
| Table | Holds |
|---|---|
| `analyses` | one row per processed statement (id, period, created_at, metrics JSON) |
| `transactions` | cleaned + categorized txns per analysis |
| `recurring_groups` | detected recurring payments per analysis |
| `category_cache` | `description_clean` → category (permanent, provider-agnostic) |
| `insight_cache` | analysis content-hash → insights/narrative text |
| `chat_history` | per-analysis conversation turns |
| `llm_usage` | per-day token tally for the budget guard |

- **Privacy:** local file only (`DB_PATH`), git-ignored; stores structured results + caches,
  not raw statement bytes or secrets.
- **Enables:** `/api/history`, `compare_months` tool, cross-month trends, and near-zero-token
  reruns (caches survive restarts).
