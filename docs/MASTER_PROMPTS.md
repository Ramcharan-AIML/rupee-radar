# RupeeRadar — Master Prompts (Phases 0–5)

This file contains **3 self-contained master prompts** that regenerate the entire RupeeRadar
project up to Phase 5, with zero detail loss. Paste each prompt (in order) into any
AI-assisted IDE (Cursor, Windsurf, Claude Code, Copilot, etc.).

- **Master Prompt 1** → Product context + architecture + all design docs (the "what & why").
- **Master Prompt 2** → Backend (Python/FastAPI), Phases 0–4 + Groq limits + sample data + tests.
- **Master Prompt 3** → Frontend (React/Vite/TS/Tailwind), Phases 0 & 5.

**Order matters.** Run 1 → 2 → 3. Prompts 2 and 3 assume the repo root from Prompt 1.

**Global ground rules (apply to all 3 prompts):**
- Stack is locked: **Python 3.11+ / FastAPI backend**, **React + Vite + TypeScript + Tailwind frontend**, **Groq `llama-3.3-70b-versatile`** as the (later-phase) LLM, **local-only** data.
- **Code does ALL math; the LLM only handles language** (never let an LLM compute a number).
- **Token discipline:** rules-first + cache, send summaries not rows, hard budgets, graceful degradation. The app must be fully usable with the LLM disabled.
- Project root used here: `RupeeRadar_project/`.

---
---

# ===================== MASTER PROMPT 1 — DESIGN & DOCS =====================

> Copy everything in this section into your IDE as one prompt.

You are setting up a new project called **RupeeRadar**. Create a `docs/` folder and generate
the following design documents EXACTLY as specified. Do not write code yet — this prompt only
produces documentation that locks all decisions.

## Product

**RupeeRadar** is an AI-powered **personal finance analyst** that converts messy bank
statement data into clean, categorized, human-readable spending insights, with an LLM
"analyst buddy" layer (insights, narrative, chat) on top of a deterministic, number-accurate
pipeline. It must answer: biggest spending categories; how much spent this month; which
payments are recurring subscriptions/EMIs; biggest transaction; top spending insights.

**Core requirements:** (1) accept statement input; (2) extract/clean into structured data;
(3) categorize into 10 canonical categories; (4) detect recurring payments; (5) compute
metrics (income, spend, savings, top categories, biggest txn); (6) generate ≥3 human-readable
insights using real amounts; (7) present via dashboard + downloadable report. Privacy-conscious
throughout. Prioritize a working end-to-end prototype over perfect support for every bank.

## Locked decisions

| Area | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn, Pydantic v2 |
| Frontend | React + Vite + TypeScript + Tailwind, Recharts |
| Categorization | **Rules-first + permanent cache + LLM fallback** |
| LLM role | Core analyst layer (fallback categorization, insights, narrative, chat) — **language only, never math** |
| LLM model | `llama-3.3-70b-versatile` via **Groq** (free), with **Ollama** local alternative behind the same interface |
| Data residency | **Local-only**; only cleaned descriptions / compact summaries ever sent to the LLM |
| Storage | Local SQLite (history, caches, usage log) — arrives Phase 7 |

## Canonical categories (the ONLY allowed categories, everywhere)

`Food, Travel, Shopping, Bills, EMI, Subscriptions, Salary, Rent, Investments, Other`
Default/fallback category = **Other**.

## Groq free-tier rate limits for `llama-3.3-70b-versatile` (HARD ceilings)

| Window | Limit | Note |
|---|---|---|
| Requests / minute (RPM) | **30** | |
| Tokens / minute (TPM) | **1,000** | **binding constraint** — keep each call tiny |
| Requests / day (RPD) | **12,000** | |
| Tokens / day (TPD) | **100,000** | caps the daily token budget |

These shape the design: a single request (prompt+input+completion) must stay well under
1,000 tokens. The budget guard (Phase 8) enforces all four windows + paces calls.

## Files to generate in `docs/`

1. **`docs/context.md`** — Problem & goal; the 5 key user questions; the 7 core requirements;
   expected deliverables; evaluation criteria (categorization accuracy, insight quality,
   real-world robustness, UX, completeness, privacy); constraints; the canonical category list.

2. **`docs/architecture.md`** — Include:
   - **§0 Guiding principles:** code does math / LLM does language; tokens are scarce
     (rules-first, cache, summaries-not-rows, hard budgets, graceful degradation); local-first;
     graceful degradation. A diagram showing the deterministic pipeline feeding a compact
     numeric summary into the LLM layer.
   - **§1 Decisions table** (as above) + the on-LLM-choice notes (Groq free tier, privacy
     trade-off, Ollama alternative).
   - **§2 System overview** (React SPA ⇄ FastAPI ⇄ in-memory/SQLite store; pipeline).
   - **§3 Backend module layout** (see Prompt 2 file tree) + **§3.2 Pydantic data model**.
   - **§4 Six pipeline stages:** ingest, clean, categorize (rules-first + cache + LLM
     fallback), recurring, metrics, insights.
   - **§5 API surface:** `/api/upload`, `/api/analysis/{id}`, `/api/history`, `/api/report`,
     `/api/chat`, `/api/usage`, `/api/health`.
   - **§6 Frontend architecture** (pages + components).
   - **§7 Privacy & security** (local-only; no raw persistence; only cleaned text/summaries to
     LLM; `.env` + `data/` git-ignored).
   - **§8 Configuration (.env)** — see Prompt 2 for the exact variables.
   - **§9 LLM provider abstraction** (`classify`/`complete`/`chat`; groq/ollama/none).
   - **§10 Tech stack summary.**
   - **§12 LLM intelligence layer** (4 roles: categorization fallback, analyst insights,
     monthly narrative, chat via tool-use NOT context-stuffing).
   - **§13 Token budget & cost control** — include the exact Groq limits table above; TPM=1,000
     is binding; budget guard enforces RPM/TPM/RPD/TPD + paces calls + 429 back-off; degrade to
     baseline when any window is hit.
   - **§14 Persistent local storage (SQLite)** — tables: `analyses`, `transactions`,
     `recurring_groups`, `category_cache`, `insight_cache`, `chat_history`, `llm_usage`.

3. **`docs/implementation-plan.md`** — 14 phases (P0–P13) in 3 bands:
   - Foundation (P0–P6, zero tokens): P0 scaffold, P1 models+session store, P2 ingest+clean,
     P3 rule categorization, P4 metrics+insights+`/api/upload`, P5 React dashboard, P6 recurring.
   - Persistence & cost control: P7 SQLite storage, P8 budget guard + cache.
   - Analyst layer (LLM): P9 LLM fallback categorization, P10 insights+narrative, P11 chat.
   - Hardening: P12 report export, P13 extra formats + hardening.
   Each phase lists goal, tasks, files, dependencies, acceptance criteria, demo checkpoint.
   Include a dependency-flow diagram, requirement→phase traceability, and milestones M1–M5.

4. **`docs/edge-cases.md`** — Catalog (severity 🔴/🟡/🟢, owning phase) covering: upload/file
   handling; ingest/column detection; date parsing (mixed formats, DD/MM vs MM/DD Indian
   default, unparseable); amount normalization (₹, Indian commas, Cr/Dr, parentheses);
   description cleaning (rail prefixes, ref numbers, PII, over-stripping, merchant variants);
   rule categorization (no match, multiple match precedence, substring false positives like
   RENTAL≠RENT, salary-credit-only, refunds, transfers, non-canonical guard); LLM fallback
   (disabled=zero calls, errors, invalid/out-of-vocab output, count mismatch, caching, prompt
   injection, privacy leak); recurring detection; metrics & insights (no income div-by-zero,
   negative savings, all-Other, empty analysis, no NaN/None); API/session/frontend; token
   budget (TPD/RPD exhaustion, 429, TPM pacing to ≤1,000, single-call-too-large); analyst
   chat (LLM-does-math forbidden, hallucinated numbers, tool errors); SQLite persistence.
   End with cross-cutting invariants: no crash on any input; every category ∈ canonical;
   no silent data loss; money conservation (income−spend==savings); no div-by-zero; privacy;
   LLM-optional parity; **LLM never computes numbers**; every LLM path cached+budget-checked+
   has fallback; determinism; never render NaN/None/undefined.

Acceptance: four readable docs exist in `docs/` and agree on the decisions, categories, and
Groq limits above.

---
---

# ===================== MASTER PROMPT 2 — BACKEND (Phases 0–4) =====================

> Copy everything in this section into your IDE as one prompt. Assumes Prompt 1's repo.

Build the **RupeeRadar backend** in `backend/`. Python 3.11+. Follow the canonical categories
and Groq limits from the design docs. Implement Phases 0–4. After each phase, ensure `pytest`
passes. Do not call any network/LLM yet (the LLM hook is a no-op stub).

## Tooling & layout

Create `.gitignore` at repo root ignoring: `.env`, `.env.local`, `data/`, `*.db`/`*.sqlite*`,
`__pycache__/`, `*.py[cod]`, `.venv/`/`venv/`, `.pytest_cache/`, `node_modules/`,
`frontend/dist/`, `*.tsbuildinfo`, `frontend/vite.config.js`, `frontend/vite.config.d.ts`,
editor/OS files. Initialize git.

`backend/requirements.txt`:
```
fastapi>=0.110
uvicorn[standard]>=0.29
python-multipart>=0.0.9
pydantic>=2.6
pydantic-settings>=2.2
pandas>=2.2
pytest>=8.0
httpx>=0.27
```

Backend tree:
```
backend/
├── app/
│   ├── __init__.py            # __version__ = "0.1.0"
│   ├── main.py                # FastAPI app + CORS + routers + root route
│   ├── config.py              # Pydantic-settings Settings (+ Groq limits, clamping)
│   ├── constants.py           # CANONICAL_CATEGORIES, helpers
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes_health.py   # GET /api/health
│   │   ├── routes_upload.py   # POST /api/upload
│   │   └── routes_analysis.py # GET /api/analysis/{session_id}
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── ingest.py
│   │   ├── clean.py
│   │   ├── rules.py
│   │   ├── categorize.py
│   │   ├── metrics.py
│   │   └── insights.py
│   ├── llm/
│   │   ├── __init__.py
│   │   └── limits.py          # authoritative Groq rate limits
│   └── store/
│       ├── __init__.py
│       └── session_store.py
├── scripts/
│   └── test_pipeline.py       # manual CLI tester
├── tests/
│   ├── sample_statements/messy_sample.csv
│   ├── test_schemas.py
│   ├── test_session_store.py
│   ├── test_clean.py
│   ├── test_categorize.py
│   ├── test_metrics.py
│   ├── test_pipeline_e2e.py
│   └── test_config_limits.py
├── pytest.ini                 # [pytest]\npythonpath = .\ntestpaths = tests
└── .env.example
```

### `app/llm/limits.py`
Frozen dataclass `RateLimits(requests_per_minute, tokens_per_minute, requests_per_day,
tokens_per_day)`. `GROQ_LIMITS = {"llama-3.3-70b-versatile": RateLimits(30, 1000, 12000,
100000)}` plus a `_GROQ_DEFAULT` with the same numbers. `limits_for(provider, model)` returns
the Groq limits for `groq` (default fallback if model unknown), else `None` (ollama/none =
unlimited).

### `app/config.py`
`Settings(BaseSettings)` with `model_config = SettingsConfigDict(env_file=".env",
env_file_encoding="utf-8", case_sensitive=False, extra="ignore")`. Fields:
- `llm_provider: Literal["groq","ollama","none"] = "groq"`, `groq_api_key=""`,
  `groq_model="llama-3.3-70b-versatile"`, `ollama_model="llama3.3"`
- Groq limits: `groq_rpm_limit=30`, `groq_tpm_limit=1000`, `groq_rpd_limit=12000`,
  `groq_tpd_limit=100000`
- Budgets: `llm_daily_token_budget=100000`, `llm_max_tokens_per_call=500`,
  `llm_categorize_batch=15`, `llm_enable_chat=True`, `llm_enable_narrative=True`,
  `llm_insight_mode: Literal["off","polish","generate"]="polish"`
- Storage/limits: `db_path="./data/rupeeradar.db"`, `session_ttl_minutes=60`, `max_upload_mb=10`
- Server: `frontend_origin="http://localhost:5173"`
- Properties: `llm_enabled` (none→False; groq→bool(key); ollama→True), `active_model`,
  `provider_limits` (→`limits_for`).
- `@model_validator(mode="after") _clamp_to_provider_limits`: if provider has limits, set
  `llm_daily_token_budget = min(budget, tokens_per_day)` and `llm_max_tokens_per_call =
  min(max_per_call, int(tokens_per_minute*0.8))`. Ollama/none not clamped.
- `@lru_cache get_settings()`.

### `.env.example` (variables, with the Groq limits + budgets above)
Include all the env keys matching the Settings fields (LLM_PROVIDER, GROQ_API_KEY, GROQ_MODEL,
OLLAMA_MODEL, GROQ_RPM_LIMIT=30, GROQ_TPM_LIMIT=1000, GROQ_RPD_LIMIT=12000,
GROQ_TPD_LIMIT=100000, LLM_DAILY_TOKEN_BUDGET=100000, LLM_MAX_TOKENS_PER_CALL=500,
LLM_CATEGORIZE_BATCH=15, LLM_ENABLE_CHAT=true, LLM_ENABLE_NARRATIVE=true,
LLM_INSIGHT_MODE=polish, DB_PATH=./data/rupeeradar.db, SESSION_TTL_MINUTES=60,
MAX_UPLOAD_MB=10, FRONTEND_ORIGIN=http://localhost:5173).

### `app/constants.py`
`CANONICAL_CATEGORIES` tuple (the 10 in order), `DEFAULT_CATEGORY="Other"`,
`CANONICAL_CATEGORY_SET=frozenset(...)`, `is_canonical(cat)->bool`,
`coerce_category(cat|None)->str` (returns cat if canonical else "Other").

### `app/models/schemas.py` (Pydantic v2)
Types: `Direction=Literal["debit","credit"]`, `CategorySource=Literal["rule","llm","default"]`,
`Cadence=Literal["weekly","monthly","quarterly","yearly","irregular"]`. `new_id()` = uuid4 hex.

- **Transaction**: `id`(default new_id), `date: date`, `description_raw: str`,
  `description_clean: str=""`, `amount: float`, `direction: Direction`,
  `category: str=DEFAULT_CATEGORY`, `category_source: CategorySource="default"`,
  `confidence: float=0.0`, `is_recurring=False`, `recurring_group_id: str|None=None`.
  Validators: amount must be ≥0 (sign is in direction); category must be canonical.
- **RecurringGroup**: `id`, `merchant`, `cadence`, `typical_amount`, `occurrences`,
  `category` (canonical-validated).
- **Metrics**: `total_income=0.0`, `total_spend=0.0`, `net_savings=0.0`, `savings_rate=0.0`,
  `top_categories: list[tuple[str,float]]=[]`, `biggest_transaction: Transaction|None=None`,
  `by_month: dict[str,float]={}`.
- **SchemaReport**: `detected_columns: dict[str,str|None]={}`, `total_rows=0`, `parsed_rows=0`,
  `dropped_rows=0`, `confidence=0.0`, `warnings: list[str]=[]`.
- **Analysis**: `session_id`(default new_id), `created_at: datetime`(default utcnow),
  `transactions=[]`, `recurring=[]`, `metrics=Metrics()`, `insights: list[str]=[]`.
- **UploadResponse**: `session_id: str`, `analysis: Analysis`, `schema_report: SchemaReport`.

### `app/store/session_store.py`
`SessionStore(ttl_minutes=60, time_fn=time.monotonic)` — thread-safe (Lock). Stores only
`Analysis` (never raw bytes). `put(analysis)->session_id` (expires_at = now + ttl*60);
`get(id)->Analysis|None` (lazily deletes expired on access); `purge()->int` (remove expired);
`clear()`; `__len__`. Module singleton `get_session_store()` reading
`get_settings().session_ttl_minutes`.

### `app/pipeline/ingest.py`
Column synonyms (compared as lowercased, alnum-only via `re.sub(r"[^a-z0-9]","",h)`):
- date: date, txndate, transactiondate, valuedate, postingdate, trandate
- description: description, narration, particulars, details, remarks, remark,
  transactiondetails, naration
- debit: debit, withdrawal, withdrawalamt, withdrawaldr, debitamount, paidout, dr, withdrawals
- credit: credit, deposit, depositamt, depositcr, creditamount, paidin, cr, deposits
- balance: balance, closingbalance, runningbalance, availablebalance, bal
- amount: amount, amt, transactionamount, txnamount
- type: type, drcr, transactiontype, crdr

`detect_columns(headers)->(mapping, warnings)`: score each header vs synonyms (3=exact,
2=substring either way, 0=none); assign in priority order
`[date, description, debit, credit, balance, amount, type]`, each header used once, highest
score wins. Warn if date/description missing or no amount/debit/credit.
`_confidence(mapping)` = round(sum([has_date, has_desc, has_amount_or_debit_or_credit])/3, 2).
`IngestResult(rows: list[dict], columns: dict, report: SchemaReport)`.
`ingest_csv(source: str|Path|bytes)`: bytes→BytesIO; `pd.read_csv(dtype=str,
keep_default_na=False, skipinitialspace=True, encoding="utf-8")`; strip header whitespace;
build rows as `{canonical: str(value).strip()}` for mapped columns; report total_rows,
detected_columns, confidence, warnings.

### `app/pipeline/clean.py`
- `parse_date(value)->date|None`: blank→None; if matches `^\d{4}-\d{1,2}-\d{1,2}` parse as ISO
  (month-first, no dayfirst); else `pd.to_datetime(s, dayfirst=True, format="mixed",
  errors="raise")`; catch errors→None.
- `parse_amount_cell(value)->float|None`: blank→None; strip surrounding `()`; remove
  `₹|rs\.?|inr` (case-insensitive), remove `\b(cr|dr)\b`, remove commas/spaces, strip
  leading `+`/`-`; empty/`.`→None; else `abs(float(s))`.
- `parse_signed_amount(value, type_hint=None)->(float,Direction)|None`: detect `\bcr\b`/`\bdr\b`
  in `value + type_hint`; is_negative if starts `-` or wrapped in `()`; magnitude via
  parse_amount_cell; default direction "debit" when no hint; if sign says negative but hint
  said credit, prefer debit.
- `clean_description(raw)->str` (uppercase): first remove VPAs `[\w.\-]+@[\w.\-]+`, then split
  on `[^A-Z0-9]+`, drop tokens that are: in NOISE_TOKENS; length 1; all digits; start "REF"+
  digits; mixed alpha+digit (ref ids). Join with spaces. Fallback: first alphabetic token
  else "UNKNOWN".
  - **NOISE_TOKENS** = {UPI, IMPS, NEFT, RTGS, POS, ACH, ATM, ECS, MMT, IB, NWD, VPS, CHQ, EMI,
    REF, REFNO, PAYMENT, PMT, FROM, TO, TXN, TRANSACTION, ID, NO, NA, P2A, P2M, BIL, BILLPAY,
    AUTOPAY, TRANSFER, TRF, VIA, CR, DR, D, C}.
  - **NON_TXN_MARKERS** = (OPENING BALANCE, CLOSING BALANCE, BALANCE B/F, BALANCE C/F, B/F,
    C/F, OPENING BAL, CLOSING BAL, TOTAL, GRAND TOTAL, STATEMENT SUMMARY).
- `clean(ingested)->CleanResult(transactions, report)`: for each row — parse date (None→drop);
  if debit/credit columns present, reconcile (both>0 → warn+drop; debit→amount/debit;
  credit→amount/credit; neither→drop); else parse_signed_amount(amount,type) (None/≤0→drop);
  if description matches a NON_TXN_MARKER → drop; build Transaction (category left default).
  Update report parsed_rows/dropped_rows/warnings (copy ingest report).
- `ingest_and_clean(source)->CleanResult` convenience.

### `app/pipeline/rules.py`
`Rule(pattern: compiled regex, category, confidence, direction: Direction|None)`. Helper `_r`
builds `re.compile(rf"\b(?:{keywords})\b", re.IGNORECASE)`. **Ordered** list (first match wins;
specific before general):
1. Subscriptions (0.95): `NETFLIX|HOTSTAR|DISNEY|SPOTIFY|GAANA|JIOSAAVN|SONYLIV|ZEE5|VOOT|AUDIBLE|YOUTUBE\s+PREMIUM|AMAZON\s+PRIME|PRIME\s+VIDEO|APPLE\.COM/BILL|SUBSCRIPTION`
2. EMI (0.9): `EMI|LOAN|HOME\s+LOAN|CAR\s+LOAN|PERSONAL\s+LOAN|BAJAJ\s+FIN|NACH`
3. Rent (0.9): `RENT|HOUSE\s+RENT`
4. Investments (0.9): `SIP|MUTUAL\s+FUND|ZERODHA|GROWW|UPSTOX|KUVERA|SMALLCASE|NPS|PPF|ELSS|COIN|INDMONEY|BROKING`
5. Salary (0.95, **direction="credit"**): `SALARY|PAYROLL|STIPEND`
6. Food (0.9): `SWIGGY|ZOMATO|RESTAURANT|DOMINOS|MCDONALD|KFC|PIZZA|BURGER|CAFE|STARBUCKS|FRESHMENU|EATCLUB|BIGBASKET|BLINKIT|ZEPTO|GROFERS|DUNZO|INSTAMART`
7. Travel (0.9): `UBER|OLA|RAPIDO|IRCTC|REDBUS|MAKEMYTRIP|GOIBIBO|YATRA|INDIGO|VISTARA|AIR\s*INDIA|SPICEJET|FUEL|PETROL|DIESEL|INDIAN\s+OIL|BHARAT\s+PETROLEUM|HPCL|IOCL|FASTAG|TOLL|METRO|PARKING|OLACABS`
8. Bills (0.85): `ELECTRICITY|BESCOM|BSES|TATA\s+POWER|ADANI\s+ELECTRICITY|RECHARGE|AIRTEL|JIO|VODAFONE|\bVI\b|BSNL|BROADBAND|DTH|GAS\s+BILL|WATER\s+BILL|POSTPAID|PREPAID|INSURANCE|\bLIC\b|PREMIUM|UTILITY`
9. Shopping (0.85): `AMAZON|FLIPKART|MYNTRA|AJIO|MEESHO|NYKAA|RELIANCE\s+DIGITAL|CROMA|IKEA|DECATHLON|LIFESTYLE|SHOPPERS\s+STOP|TATA\s+CLIQ|SNAPDEAL|DMART|RELIANCE\s+TRENDS`

`match_category(description_clean, direction)->(category,confidence)|None`: skip rules whose
direction != txn direction; first regex match wins. Import-time guard asserts every rule's
category is canonical. (Note: "EMI" word is stripped during cleaning, so EMI rule relies on
LOAN/HOME LOAN.)

### `app/pipeline/categorize.py`
`categorize_transactions(transactions, provider=None)->list`: for each txn, `match_category`;
if matched → category=coerce_category(cat), source="rule", confidence; else → "Other",
"default", 0.0. Then call `_llm_fallback(transactions, provider)` which is a **no-op** (Phase 9
fills it). `provider` param accepted but ignored.

### `app/pipeline/metrics.py`
`compute_metrics(transactions)->Metrics`: empty→`Metrics()`. debits/credits split;
total_income=Σcredits, total_spend=Σdebits, net_savings=income−spend,
savings_rate=net/income if income>0 else 0.0. top_categories = spend by category (debits),
sorted by `(-amount, category)`. biggest_transaction = `max(debits, key=(amount, date))` (tie→
latest date) or None. by_month = debit spend keyed "YYYY-MM", returned sorted.

### `app/pipeline/insights.py`
`generate_insights(transactions, metrics)->list[str]` (≥3, amounts via `₹{x:,.0f}`): empty→
single "No valid transactions were found…" message. Else: (1) top category + % of spend;
(2) total spend across N debit txns; (3) savings (income>0: saved ₹X = Y% of income; or
overspent; else "No income detected…"); (4) biggest single expense (₹, merchant.title(),
`%d %b %Y`); (5) subscriptions-spend placeholder if any. Never emit None/NaN.

### `app/api/routes_health.py`
`GET /api/health` → `{status:"ok", version, llm_provider, llm_enabled, model}` (Pydantic
response model). Router prefix `/api`.

### `app/api/routes_upload.py`
`POST /api/upload` (`UploadFile`): reject non-`.csv`/`.txt` filename → 415; empty bytes → 400;
> max_upload_mb → 413; parse via `ingest_and_clean(bytes)` in try/except → 422 on failure (never
500). Then categorize → compute_metrics → generate_insights → build `Analysis(transactions,
recurring=[], metrics, insights)` → `get_session_store().put` → return `UploadResponse`.

### `app/api/routes_analysis.py`
`GET /api/analysis/{session_id}` → stored Analysis or 404.

### `app/main.py`
`create_app()`: FastAPI(title="RupeeRadar API", version=__version__); CORS allow
`settings.frontend_origin`, credentials, all methods/headers; include health, upload, analysis
routers; root `GET /` → `{name, docs:"/docs", health:"/api/health"}`. `app = create_app()`.

### `backend/scripts/test_pipeline.py`
Manual CLI: arg = CSV path (default `../sample_data/rupeeradar_sample_statement.csv`);
`sys.path.insert` the backend dir; `ingest_and_clean` → `categorize_transactions`; print
detected columns, schema report (total/parsed/dropped/confidence, warnings), a table
(date, direction, amount, category, source, clean merchant), totals, and spend-by-category.
**Use "Rs" not ₹ in console prints** (Windows cp1252 can't encode ₹).

### Sample data

`backend/tests/sample_statements/messy_sample.csv` (13 rows, 9 valid txns):
```
Txn Date,Narration,Chq/Ref No,Withdrawal (Dr),Deposit (Cr),Closing Balance
01/01/2025,OPENING BALANCE B/F,,,,"₹1,00,000.00"
02/01/2025,UPI/SWIGGY*ORDER/427183920@okhdfcbank/Payment from,427183920,₹458.00,,"99,542.00"
05-01-2025,NEFT-CR-ACME CORP SALARY JAN-REF99281,N99281,,"₹85,000.00","1,84,542.00"
07 Jan 2025,POS/AMAZON INDIA PVT LTD/REF8842,8842,"1,299.00",,"1,83,243.00"
2025-01-10,ACH/D/NETFLIX COM/SUBSCRIPTION/8829102,8829102,499.00,,"1,82,744.00"
10/01/2025,IMPS/P2A/HDFC/RENT PAYMENT/LANDLORD,550012,"25,000.00",,"1,57,744.00"
Txn Date,Narration,Chq/Ref No,Withdrawal (Dr),Deposit (Cr),Closing Balance
15/01/2025,UPI/ZOMATO/ORDER/REF7712,77120,612.50,,"1,57,131.50"
20/01/2025,ATM/NWD/CASH WITHDRAWAL/HDFC ATM,9001,"5,000.00",,"1,52,131.50"
25/01/2025,UPI/UBER INDIA/TRIP/REF5521,5521,342.00,,"1,51,789.50"
28/01/2025,NEFT/ZERODHA/SIP MUTUAL FUND,Z551,"10,000.00",,"1,41,789.50"
31/01/2025,CLOSING BALANCE C/F,,,,"1,41,789.50"
,TOTAL,,"42,212.50","85,000.00",
```

`sample_data/rupeeradar_sample_statement.csv` (35 rows, 31 valid txns; richer 2-month sample —
salary, rent, Swiggy/Zomato, Netflix/Spotify/Prime, Amazon/Flipkart, Uber, electricity/
recharge, EMI/home loan, Zerodha SIP, fuel, pharmacy, plus unknowns BBPS/XYZ ENTERPRISES,
APOLLO PHARMACY, CREDIT INTEREST). Columns: `Txn Date,Narration,Chq/Ref No,Withdrawal (Dr),
Deposit (Cr),Closing Balance`. Include opening/closing balance rows, a repeated header row mid-
file, and a no-date TOTAL row; mixed date formats; ₹ + Indian commas; Cr in deposits. Expected
totals: credits ₹190,412; debits ₹107,599; biggest debit Rent ₹22,000; top categories
Rent ₹44,000, Investments ₹20,000, EMI ₹17,000.

### Tests (acceptance)
- `test_schemas.py`: round-trip JSON for Transaction/Analysis/UploadResponse (incl. top_categories
  tuples survive); all canonical categories accepted; non-canonical & negative amount rejected;
  empty Analysis valid (biggest_transaction None).
- `test_session_store.py`: put/get; unknown→None; available before TTL, gone after (fake clock);
  purge removes only expired; lazy purge on get.
- `test_clean.py`: detect_columns maps the Indian headers; ingest report total=13, confidence
  1.0; clean → 9 txns (4 dropped); balance/header/total excluded; mixed dates → correct ISO;
  amounts/direction reconciled (SWIGGY 458 debit, SALARY 85000 credit, RENT 25000 debit);
  description cleaning strips noise (no UPI/REF/@/digits); parse_amount_cell & parse_signed_amount
  & parse_date parametrized cases; clean_description never empty.
- `test_categorize.py`: sample categories (SWIGGY→Food, SALARY→Salary, AMAZON→Shopping,
  NETFLIX→Subscriptions, RENT→Rent, ZOMATO→Food, UBER→Travel, ZERODHA SIP→Investments);
  matched→source "rule"; unknown→Other/default; all canonical; AMAZON PRIME→Subscriptions
  (precedence); RENTAL≠Rent; Salary only on credit; no-match→None.
- `test_metrics.py`: totals reconcile (income 85000, spend 43210.5); savings_rate in (0,1);
  top_categories sorted desc (Rent first); biggest = largest debit 25000; by_month has 2025-01;
  empty→zeros & None; no-income→savings_rate 0; tie→latest date. Insights ≥3 & cite amounts;
  empty→1 message; no None/NaN text.
- `test_pipeline_e2e.py` (FastAPI TestClient): upload sample → 200, 9 txns, ≥3 insights,
  income−spend==savings, income 85000, parsed_rows 9, detected date col; GET analysis roundtrip;
  unknown id→404; empty file→400; .pdf→415; all categories canonical.
- `test_config_limits.py`: known Groq limits (30/1000/12000/100000); ollama/none→None unlimited;
  defaults within limits; oversized settings clamped (budget→100000, max_per_call≤800);
  ollama not clamped. Use `Settings(_env_file=None, ...)` to ignore local `.env`.

### Verify
```
cd backend && python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pytest -q                 # all green
.venv/Scripts/python scripts/test_pipeline.py     # prints cleaned+categorized sample
.venv/Scripts/python -m uvicorn app.main:app --reload   # then POST /api/upload at /docs
```
Acceptance: pytest fully green; `/api/upload` returns a valid Analysis JSON; `/api/analysis/{id}`
roundtrips; config provably within all four Groq windows.

---
---

# ===================== MASTER PROMPT 3 — FRONTEND (Phases 0 & 5) =====================

> Copy everything in this section into your IDE as one prompt. Assumes Prompts 1–2's repo and a
> running backend on :8000.

Build the **RupeeRadar frontend** in `frontend/` with Vite + React 18 + TypeScript + Tailwind +
Recharts. It uploads a CSV to the backend and renders a dashboard. All currency in Indian
locale (`en-IN`, ₹).

## Scaffold & config

`frontend/package.json` — type module; scripts `dev`=vite, `build`=`tsc -b && vite build`,
`preview`. deps: `react@^18.3.1`, `react-dom@^18.3.1`, `recharts@^2.12.7`. devDeps:
`@types/react@^18.3.3`, `@types/react-dom@^18.3.0`, `@vitejs/plugin-react@^4.3.1`,
`autoprefixer@^10.4.19`, `postcss@^8.4.39`, `tailwindcss@^3.4.6`, `typescript@^5.5.3`,
`vite@^5.3.4`.

- `vite.config.ts` — React plugin; dev server port **5173**; proxy `"/api" → http://localhost:8000`
  (`changeOrigin: true`). So the app calls same-origin `/api/...`.
- `tsconfig.json` (strict, `noUnusedLocals`, `noUnusedParameters`, jsx react-jsx, bundler
  resolution, `noEmit`) + `tsconfig.node.json` (composite=true, **no** `noEmit`, include
  vite.config.ts, `tsBuildInfoFile` under node_modules/.tmp).  ← composite project must emit.
- `tailwind.config.js` (content: index.html + ./src/**/*.{ts,tsx}), `postcss.config.js`
  (tailwindcss + autoprefixer), `index.html` (root div + /src/main.tsx),
  `src/index.css` (@tailwind base/components/utilities), `src/vite-env.d.ts`,
  `src/main.tsx` (ReactDOM createRoot StrictMode).

## Source files

`src/types.ts` — TS mirrors of backend schemas: `Direction`, `Transaction`, `RecurringGroup`,
`Metrics` (note `top_categories: [string, number][]`, `biggest_transaction: Transaction|null`,
`by_month: Record<string,number>`), `Analysis`, `SchemaReport`, `UploadResponse`.

`src/lib/format.ts` — `formatInr(amount, decimals=false)` via `Intl.NumberFormat("en-IN",
{style:"currency", currency:"INR", maximumFractionDigits:0})` (and a 2-decimal variant);
`formatDate(iso)` via `Intl.DateTimeFormat("en-IN",{day:"2-digit",month:"short",year:"numeric"})`
(guard invalid date → return raw); `formatPct(rate)` → `${Math.round(rate*100)}%`.

`src/api/client.ts` — `BASE="/api"`; `handle<T>(res)` throws `Error(body.detail || HTTP n)` on
non-ok; `uploadStatement(file): Promise<UploadResponse>` (FormData POST `/api/upload`);
`getAnalysis(id): Promise<Analysis>` (GET `/api/analysis/{id}`).

`src/components/SummaryCards.tsx` — 4 cards from Metrics: Total Income (green), Total Spend
(red), Net Savings (green/red by sign, sub = `formatPct(savings_rate)` of income or "no income
detected"), Biggest Expense (indigo, sub = merchant or "—"). Reusable `Card` subcomponent.

`src/components/CategoryChart.tsx` — Recharts `PieChart` of `metrics.top_categories` mapped to
`{name, value}`; 10-color palette; `Tooltip` formats values with `formatInr`; `Legend`; empty
state when no spend. Wrap in `ResponsiveContainer` height 300, card container.

`src/components/InsightsPanel.tsx` — "💡 Insights" card; numbered list of `insights` strings.

`src/components/TransactionTable.tsx` — searchable table (state `query`; filter on
description_clean + description_raw + category, case-insensitive). Columns: Date (formatDate),
Merchant (description_clean), Category (colored badge per category via a
`CATEGORY_COLORS` map keyed by the 10 categories), Amount (right-aligned, tabular-nums,
credit green with "+", debit with "−", `formatInr(amount, true)`). Show "(X of Y)" count and an
empty-results row.

`src/pages/Upload.tsx` — drag-drop zone (`onDragOver/onDragLeave/onDrop`) + click-to-browse
(hidden `<input type="file" accept=".csv,.txt">`); on file → `uploadStatement` with busy +
error states; on success call `onUploaded(result)`. "Your data is processed locally" note.

`src/pages/Dashboard.tsx` — props `{data: UploadResponse}`. Top banner: "Parsed N of M rows ·
K non-transaction rows skipped · W warning(s)" from `schema_report`. Then `<SummaryCards>`, a
2-col grid of `<CategoryChart>` + `<InsightsPanel>`, then `<TransactionTable>`.

`src/App.tsx` — header (📡 RupeeRadar + "personal finance analyst"; "Upload new" button when an
analysis is loaded) + `useState<UploadResponse|null>`; render `<Upload onUploaded=setData>` or
`<Dashboard data=...>`.

## Verify
```
cd frontend && npm install && npm run build      # TypeScript + Vite build clean
npm run dev                                       # http://localhost:5173 (backend on :8000)
```
Acceptance: with the backend running, open :5173, drag in
`sample_data/rupeeradar_sample_statement.csv` → see summary cards, category pie chart, ≥3
insights, and a searchable transaction table; all amounts/dates in Indian locale. Upload through
the Vite proxy (`:5173/api/upload`) returns 200.

---
---

## Reproduction checklist (what "done through Phase 5" means)

- [ ] `docs/` has context, architecture, implementation-plan, edge-cases (Prompt 1).
- [ ] Backend: scaffold + config (with Groq limits & clamping) + schemas + session store +
      ingest/clean + rules/categorize + metrics/insights + `/api/health|upload|analysis`.
- [ ] Groq limits captured in `app/llm/limits.py` (RPM 30 / TPM 1000 / RPD 12000 / TPD 100000);
      config auto-clamps (budget 100000, max_tokens 500, batch 15).
- [ ] Sample CSVs + `scripts/test_pipeline.py` runner.
- [ ] `pytest` fully green (~95 tests across the 6 test files).
- [ ] Frontend: Vite/React/TS/Tailwind + Recharts dashboard; proxy to :8000; ₹/Indian locale.
- [ ] End-to-end: upload sample on the website → dashboard with cards, pie chart, insights, table.

## Not yet built (future phases, on request)

P6 recurring detection · P7 SQLite persistence + `/api/history` · P8 budget guard + cache +
`/api/usage` (live enforcement of the 4 Groq windows + TPM pacing) · P9 Groq LLM fallback
categorization · P10 analyst insights + monthly narrative · P11 chat (tool-use) · P12 report
export (PDF/CSV) · P13 XLSX/PDF ingest + hardening.

> **Security reminder:** never commit `.env`. Put your real `GROQ_API_KEY` only in
> `backend/.env` (git-ignored). Rotate any key that gets shared.
