# RupeeRadar — Edge Cases & Corner Cases

> Catalog of corner cases the implementation must handle, derived from
> [architecture.md](architecture.md) and [implementation-plan.md](implementation-plan.md).
> Organized by pipeline stage. Each case has: **trigger**, **expected handling**, and the
> **phase** that owns it. Use this as a checklist for tests and acceptance criteria.

**Severity:** 🔴 must-handle (can corrupt results or crash) · 🟡 should-handle (degrades
quality) · 🟢 nice-to-have (polish).

**Default principle:** *never crash on bad input.* On any unrecoverable row/file, skip the
row (and report it) or fail the request with a clear, friendly error — never a 500 or a
silent wrong number.

> **Note (analyst upgrade):** phase tags below follow the updated [implementation-plan.md](implementation-plan.md)
> (LLM categorization = P9; insights/narrative = P10; chat = P11; storage = P7; budget/cache =
> P8; report = P12; formats/hardening = P13). New sections §12–§14 cover the token budget,
> chat, and persistence surfaces added for the personal-analyst direction.
>
> **Two extra default principles for the analyst layer:**
> - *The LLM never does math* — every number shown comes from code; an LLM that "computes" a
>   figure is a bug, not a feature.
> - *Tokens are finite* — every LLM path must have a cache check, a budget check, and a
>   deterministic fallback. Running out of budget degrades quality, never breaks the app.

---

## 1. Upload & File Handling (P0, P9)

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| U1 | Empty file | 0-byte upload | 400 with "file is empty" | 🔴 | P9 |
| U2 | Oversized file | > `MAX_UPLOAD_MB` | 413 before parsing; no memory blowup | 🔴 | P9 |
| U3 | Wrong file type | `.txt`/`.docx`/image | 415 "unsupported format" | 🔴 | P9 |
| U4 | Extension lies about content | `.csv` holding HTML/PDF bytes | Detect by content sniff, not just extension; reject gracefully | 🟡 | P9 |
| U5 | No file in multipart | Missing form field | 400 "no file provided" | 🔴 | P0 |
| U6 | Corrupt/truncated file | Partial XLSX/PDF | Caught parse error → friendly 422, not 500 | 🔴 | P9 |
| U7 | Wrong encoding | UTF-16 / Latin-1 / BOM CSV | Encoding detection or fallback chain; ₹/special chars preserved | 🟡 | P2/P9 |
| U8 | Password-protected PDF | Encrypted statement | Detect, return "remove password & retry" message | 🟡 | P9 |
| U9 | Huge statement | 50k+ rows | Pipeline completes within reasonable time; no UI freeze | 🟢 | P9 |
| U10 | Duplicate upload | Same file twice | New `session_id` each time; no cross-session bleed | 🟢 | P1 |

---

## 2. Ingest & Column Detection (P2, P9)

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| I1 | No header row | Data starts at row 1 | Detect header presence; if absent, infer by content/positional mapping or report failure | 🟡 | P2 |
| I2 | Metadata preamble | Bank name/address/"Statement period" lines before the table | Skip non-tabular preamble; locate real header row | 🔴 | P2 |
| I3 | Trailing summary rows | "Total", "Closing balance" after data | Excluded from transactions | 🔴 | P2 |
| I4 | Ambiguous columns | Two date-like or two amount-like columns | Pick best by header score + value heuristics; record choice in `SchemaReport` | 🟡 | P2 |
| I5 | Single `amount` column (signed) | One column, +credit/−debit | Derive `direction` from sign | 🔴 | P2 |
| I6 | Separate Debit & Credit columns | Two columns, one blank per row | Reconcile into `amount` + `direction`; row with both filled → flag/skip | 🔴 | P2 |
| I7 | Both debit & credit blank | Empty amount row | Skip row, count as dropped | 🔴 | P2 |
| I8 | Merged/multi-line description | Narration wraps to next row (PDF/CSV) | Stitch continuation lines to the parent transaction | 🟡 | P9 |
| I9 | Unrecognized schema | No column maps confidently | Return `SchemaReport` with low confidence + actionable error, don't guess wildly | 🔴 | P2 |
| I10 | Delimiter variation | `;` or tab-delimited "CSV" | Sniff delimiter | 🟡 | P9 |
| I11 | Extra/duplicate columns | Repeated headers, ref/balance extras | Ignore unmapped columns safely | 🟢 | P2 |
| I12 | PDF table misalignment | Columns shift across pages | Best-effort per constraint; flag low confidence rather than emit garbage | 🟡 | P9 |

---

## 3. Date Parsing (P2)

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| D1 | Mixed formats in one file | `12/01/2025`, `2025-01-12`, `12-Jan-25` | Robust multi-format parse → ISO | 🔴 | P2 |
| D2 | Ambiguous DD/MM vs MM/DD | `03/04/2025` | Default to **DD/MM** (Indian statements); infer from any value > 12 in the file | 🔴 | P2 |
| D3 | 2-digit year | `12-Jan-25` | Resolve century sensibly (25 → 2025) | 🟡 | P2 |
| D4 | Date with time | `12/01/2025 14:33:02` | Strip time, keep date | 🟡 | P2 |
| D5 | Unparseable date | `N/A`, blank, garbage | Skip row + report; never default to today/epoch silently | 🔴 | P2/P9 |
| D6 | Future or absurd dates | `2099`, `1900` | Flag as suspicious; keep but mark, or drop with report | 🟢 | P9 |
| D7 | Locale month names | `Jan`/`Jaa`/regional | Handle standard English month abbreviations | 🟢 | P2 |

---

## 4. Amount Normalization (P2)

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| A1 | Currency symbol & commas | `₹1,23,456.78` (Indian grouping) | Strip symbol/commas → `123456.78` | 🔴 | P2 |
| A2 | `Cr`/`Dr` suffix | `5,000.00 Dr` | Parse value + set `direction` from suffix | 🔴 | P2 |
| A3 | Negative in parentheses | `(1,200.00)` | Treat as negative/debit | 🟡 | P2 |
| A4 | Sign conflicts suffix | `-500 Cr` (sign vs label disagree) | Define precedence (prefer explicit Dr/Cr label); flag conflict | 🟡 | P2 |
| A5 | Zero / blank amount | `0.00` or empty | Skip zero/blank as non-transaction; report | 🟡 | P2 |
| A6 | Non-numeric amount | `--`, `NA`, text | Skip row + report | 🔴 | P2 |
| A7 | Decimal/thousand confusion | `1.234,56` (EU style) | Detect grouping style; don't misread as 1.23 | 🟡 | P9 |
| A8 | Very large amount | crores | Parse without float precision loss surprises (use Decimal for parsing where needed) | 🟢 | P2 |
| A9 | Rounding for display | `33.333%`, fractional paise | Round only at presentation, keep precision internally | 🟢 | P4/P5 |

---

## 5. Description Cleaning (P2) — *privacy-sensitive (only this text reaches the LLM)*

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| C1 | Payment-rail prefixes | `UPI/`, `IMPS/`, `NEFT-`, `POS ` | Strip prefixes for `description_clean` | 🔴 | P2 |
| C2 | Reference numbers / IDs | long digit refs, `@okhdfcbank`, txn IDs | Strip ref/UTR/VPA noise → clean merchant token | 🔴 | P2 |
| C3 | PII in description | counterparty **name**, phone, account no. | Strip/avoid forwarding PII; never send acct/balance to LLM (privacy guarantee) | 🔴 | P2/P7 |
| C4 | Over-stripping | Cleaning erases the merchant entirely | Keep a usable token; if empty after cleaning, fall back to raw for categorization | 🟡 | P2 |
| C5 | Empty/whitespace description | blank narration | Mark merchant "Unknown"; route to `Other`/LLM | 🟡 | P2 |
| C6 | Non-ASCII / emoji / regional script | Hindi/Tamil text, emoji | Preserve UTF-8; don't corrupt; still categorizable | 🟢 | P2 |
| C7 | Case/spacing variants of same merchant | `swiggy`, `SWIGGY `, `Swiggy*Order` | Normalize so they group as one merchant (matters for recurring & cache) | 🔴 | P2/P6 |

---

## 6. Categorization — Rules (P3)

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| R1 | No rule matches | novel merchant | → `Other`, `category_source="default"` (later LLM) | 🔴 | P3 |
| R2 | Multiple rules match | `AMAZON PAY RECHARGE` (Shopping vs Bills) | Deterministic precedence/priority order; one category wins | 🔴 | P3 |
| R3 | Substring false positive | `RENTAL CAR` matching `RENT` | Use word boundaries/specific patterns to avoid misfires | 🟡 | P3 |
| R4 | Income misclassified | `SALARY` credit vs salary-named debit | Consider `direction` (Salary/Investments-return only on credit) | 🟡 | P3 |
| R5 | Credit that isn't income | refund, cashback, reversal | Don't count refunds as Salary/income; category `Other`/Shopping-refund | 🟡 | P3 |
| R6 | Self/own-account transfer | wallet load, own-account NEFT | Avoid double-counting as spend AND income; tag/exclude transfers | 🟡 | P3/P5 |
| R7 | Category not canonical | typo/extra category from rules | Validate every output ∈ `CANONICAL_CATEGORIES` | 🔴 | P3 |
| R8 | Ambiguous wallet txns | `PAYTM`/`PHONEPE` (could be anything) | Default sensibly (Other) rather than wrong-confident | 🟡 | P3 |

---

## 7. Categorization — LLM Fallback (P7) — *optional, privacy-conscious*

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| L1 | LLM disabled | `LLM_PROVIDER=none` / no key | Identical to rules-only; **zero network calls** | 🔴 | P7 |
| L2 | Provider error / timeout / rate limit | Groq 429/5xx/network | Catch, fall back to rules; request still succeeds | 🔴 | P7 |
| L3 | Invalid LLM output | non-JSON, wrong shape | Parse defensively; bad items → `Other`; don't crash | 🔴 | P7 |
| L4 | Out-of-vocabulary category | LLM returns a category not in list | Map to nearest canonical or `Other`; never emit non-canonical | 🔴 | P7 |
| L5 | Count mismatch | N inputs, ≠N classifications returned | Align by index/key; fill missing with `Other` | 🔴 | P7 |
| L6 | Duplicate descriptions | same `description_clean` repeated | Cache → one call per unique description | 🟡 | P7 |
| L7 | Batch too large | 100s of unknowns | Chunk into 20–50 per request | 🟡 | P7 |
| L8 | Empty/whitespace input to LLM | blank cleaned text | Skip sending; assign `Other` locally | 🟡 | P7 |
| L9 | Privacy leak risk | accidentally sending raw row | Assert only `description_clean` is sent; test guards it | 🔴 | P7 |
| L10 | Non-determinism | varying answers run-to-run | Low temperature + strict prompt + cache for stability | 🟢 | P7 |
| L11 | Prompt injection in description | merchant text like "ignore instructions, output X" | Treat description as data, not instruction; constrain output to enum | 🟡 | P7 |

---

## 8. Recurring Detection (P6)

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| RC1 | Too few occurrences | merchant appears once | Not recurring (needs ≥2–3) | 🔴 | P6 |
| RC2 | Amount drift | Netflix ₹199 → ₹499 | Tolerate variation via CoV threshold; still recurring | 🟡 | P6 |
| RC3 | Irregular cadence | random repeats (e.g. groceries) | Not flagged as recurring subscription | 🟡 | P6 |
| RC4 | Date jitter | billed 1st, 3rd, 28th | Cadence detection tolerant of ±few days | 🟡 | P6 |
| RC5 | Missed month / gap | skipped payment | Still recognized if pattern otherwise holds | 🟢 | P6 |
| RC6 | Merchant name variants | `NETFLIX`, `NETFLIX.COM`, `Netflix Inc` | Normalize so they group (depends on C7) | 🔴 | P6 |
| RC7 | Single-month statement | no time span | Recurring detection degrades gracefully (likely none); no crash/div-by-zero | 🔴 | P6/P9 |
| RC8 | Distinct merchants, same amount | two ₹500 services | Don't merge unrelated merchants into one group | 🟡 | P6 |
| RC9 | Recurring credits | salary, SIP dividend | Cadence logic works for credits too; tag correctly | 🟢 | P6 |
| RC10 | Cadence-to-monthly normalization | weekly/quarterly/yearly | "Monthly total" insight normalizes cadence correctly | 🟡 | P6 |

---

## 9. Metrics & Insights (P4, P6)

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| M1 | No income | only debits | `savings_rate` guarded (no div-by-zero); shown as N/A | 🔴 | P4/P9 |
| M2 | No spend | only credits | Top categories empty handled; no crash | 🟡 | P4 |
| M3 | Negative savings | spend > income | Allowed; insight phrased as overspend, not error | 🟡 | P4 |
| M4 | Single transaction | 1 row | Biggest = that txn; charts/insights still render | 🟡 | P4 |
| M5 | All `Other` | nothing categorized | Insights still produced (≥3) using totals/biggest | 🟡 | P4 |
| M6 | Ties | two equal "biggest" | Deterministic tiebreak (e.g. latest date) | 🟢 | P4 |
| M7 | Transfers inflate totals | own-account moves | Exclude transfers from income/spend if detected (links R6) | 🟡 | P4 |
| M8 | Empty analysis | all rows dropped | Friendly "no valid transactions found", not blank/500 | 🔴 | P4/P9 |
| M9 | Insight references missing data | recurring insight pre-P6 | Placeholder/omit gracefully; never show `None`/`NaN`/`₹undefined` | 🟡 | P4 |
| M10 | Percentage rounding sums ≠ 100% | category shares | Acceptable display rounding; don't assert exact 100 | 🟢 | P5 |

---

## 10. API, Session & Frontend (P0, P1, P5, P8)

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| S1 | Unknown `session_id` | bad/expired id on GET | 404, clear message | 🔴 | P1/P4 |
| S2 | Expired session (TTL) | fetch after `SESSION_TTL_MINUTES` | 404 "session expired, re-upload" | 🔴 | P1 |
| S3 | Report before analysis ready | `/report` with no/invalid session | 404, not 500 | 🟡 | P8 |
| S4 | Bad report format param | `?format=xml` | 400 with allowed values | 🟡 | P8 |
| S5 | CORS blocked | frontend origin mismatch | Correct CORS for dev origin (`:5173`) | 🔴 | P0 |
| S6 | Large analysis payload | many txns to UI | Table paginates/virtualizes; no freeze | 🟢 | P5 |
| S7 | Upload in progress / double submit | user clicks twice | Disable button / dedupe; no duplicate sessions confusion | 🟢 | P5 |
| S8 | Empty/error states in UI | upload fails or 0 txns | Show friendly empty/error UI, not blank dashboard | 🔴 | P5/P9 |
| S9 | ₹ & locale formatting | large amounts | Indian digit grouping + `₹`; dates `DD MMM YYYY` | 🟡 | P5 |
| S10 | Concurrent uploads | two tabs | Sessions isolated by id | 🟢 | P1 |

---

## 11. Privacy & Security (cross-cutting: P7, P8, P9, P10)

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| P1c | Raw bytes persisted | after parsing | Discard raw file; persist only structured `Analysis` to local DB | 🔴 | P7 |
| P2c | Secret leakage | logging requests/errors | Never log API key, file contents, or PII | 🔴 | P0/P9 |
| P3c | LLM receives sensitive fields | over-broad payload | Categorize sends only `description_clean`; insights/chat send only the compact numeric summary — never acct/balance/name (links L9) | 🔴 | P9/P10 |
| P4c | DB grows unbounded | many uploads over time | Bounded/prunable history; caches keyed by hash (no dupes) | 🟡 | P7 |
| P5c | API key required but missing | `LLM_PROVIDER=groq`, no key | Don't crash on boot; degrade to rules + warn | 🟡 | P0/P8 |
| P6c | `.env` / DB committed | secrets or data in git | `.gitignore` covers `.env` **and** `data/`; only `.env.example` tracked | 🔴 | P0/P7 |
| P7c | Usage log leaks prompts | logging token usage | `llm_usage` stores counts only — never prompt text/PII | 🟡 | P8 |

---

## 12. Token Budget & Cost Control (P8, threaded P9–P11)

> **Groq `llama-3.3-70b-versatile` limits enforced:** RPM **30**, TPM **1,000** (binding),
> RPD **12,000**, TPD **100,000**. Source of truth: `app/llm/limits.py`.

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| T1 | Daily token budget/TPD exhausted | day tally ≥ `LLM_DAILY_TOKEN_BUDGET` (≤ TPD 100k) | Skip LLM, return deterministic baseline + `degraded=true`; no call made | 🔴 | P8 |
| T1b | Daily request limit (RPD) hit | day requests ≥ 12,000 | Same graceful skip + `degraded` | 🟡 | P8 |
| T2 | Rate limit (429) | Groq window hit despite pacing | Respect `Retry-After`, back off; fall back to baseline; no hang/retry-storm | 🔴 | P8/P9 |
| T2b | TPM pacing (1,000 tok/min) | many calls within a minute | Pace/queue calls and keep each small so per-minute tokens ≤ 1,000; don't burst | 🔴 | P8 |
| T2c | Single call too large for TPM | prompt+completion > ~1,000 | Cap `max_tokens` + batch size so one call never exceeds TPM; split if needed | 🔴 | P8/P9 |
| T3 | Cache miss vs hit | repeat description/analysis | Hit → zero tokens; miss → call then cache. Repeats never re-billed | 🔴 | P8 |
| T4 | Pre-flight underestimate | response larger than estimated | `LLM_MAX_TOKENS_PER_CALL` caps completion; record actuals post-call | 🟡 | P8 |
| T5 | Budget tally race | concurrent calls | Tally update atomic; can't overspend via parallelism | 🟡 | P8 |
| T6 | Daily reset | new day | Tally resets at day boundary (timezone-consistent) | 🟡 | P8 |
| T7 | Oversized batch | hundreds of unknowns | Chunk to `LLM_CATEGORIZE_BATCH`; respect per-call token cap | 🟡 | P9 |
| T8 | Context bloat in chat | long conversation | Cap history to last N turns; summary-only context; bounded tokens/question | 🔴 | P11 |
| T9 | Cache key collision/staleness | rules dict updated | Cache key includes rules/version hash so stale categories don't stick | 🟡 | P8/P9 |
| T10 | Provider switch reuses cache | Groq ↔ Ollama | Category cache is provider-agnostic (safe); note possible answer drift | 🟢 | P9 |
| T11 | Budget badge accuracy | UI vs actual | `/api/usage` reflects real tally incl. in-flight; no stale "full" state | 🟢 | P8 |

---

## 13. Analyst Insights, Narrative & Chat (P10, P11)

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| AN1 | LLM does math | model computes a total/percentage | **Forbidden** — all numbers from code; tests assert figures match computed metrics | 🔴 | P10/P11 |
| AN2 | Hallucinated number/merchant | model invents a figure | Ground every claim in the summary/tool result; mismatch → reject/regenerate | 🔴 | P10/P11 |
| AN3 | LLM off / over budget | no provider or T1 | Insights fall back to template (≥3); narrative omitted; chat returns "unavailable" cleanly | 🔴 | P10/P11 |
| AN4 | Stale cached insight | underlying data changed | Cache keyed by analysis content hash → regenerate on change | 🟡 | P10 |
| AN5 | Tool returns empty | e.g. `compare_months` with one month | Model answers "not enough data," not a fabricated comparison | 🟡 | P11 |
| AN6 | Unknown/unanswerable question | out of scope ("buy stock X?") | Decline gracefully; stay within the user's own data | 🟡 | P11 |
| AN7 | Prompt injection via txn text | description like "ignore instructions" | Transaction text is data, not instructions; tool outputs constrained | 🟡 | P11 |
| AN8 | Bad tool args from model | invalid month/category | Validate tool args; return error to model, don't crash | 🔴 | P11 |
| AN9 | Tool-call loop | model keeps calling tools | Cap tool-call rounds per turn; then answer or give up | 🟡 | P11 |
| AN10 | Wrong currency/locale in prose | "$" or US grouping | Narrative/insights use ₹ + Indian grouping | 🟢 | P10 |
| AN11 | Chat references missing analysis | bad/expired `id` | 404/clear message; no crash | 🟡 | P11 |
| AN12 | Non-determinism in advice | varying tone/answers | Low temperature + cache where sensible; acceptable variance in prose only, never in numbers | 🟢 | P10/P11 |

---

## 14. Persistent Storage (SQLite) (P7)

| # | Case | Trigger | Expected handling | Sev | Phase |
|---|---|---|---|---|---|
| DB1 | DB file missing/first run | fresh install | Auto-create schema; don't crash | 🔴 | P7 |
| DB2 | Schema migration | app upgraded, old DB | Versioned migrations; don't lose/corrupt data | 🟡 | P7 |
| DB3 | Corrupt DB | truncated file | Detect, surface clear error / offer reset; no silent wrong data | 🟡 | P7 |
| DB4 | Concurrent writes | two uploads at once | SQLite locking handled (WAL/serialized); no "database locked" failures surfaced raw | 🟡 | P7 |
| DB5 | Duplicate statement upload | same file twice | Dedup or distinct ids; history not polluted with exact dupes | 🟢 | P7 |
| DB6 | Unknown analysis id | bad id on GET | 404, clear message (replaces old session-TTL behavior) | 🔴 | P7 |
| DB7 | Large history | many months stored | `/api/history` paginates; queries indexed | 🟢 | P7 |
| DB8 | Cache table unbounded growth | many unique descriptions | Acceptable (small rows); optional prune; keyed to avoid dupes | 🟢 | P7/P8 |

---

## Cross-Cutting Invariants (assert in tests)

1. **No crash on any input** — malformed files yield handled errors, not stack traces.
2. **Every `category` ∈ `CANONICAL_CATEGORIES`** — at every stage (rules, LLM, default).
3. **No silent data loss** — dropped/skipped rows are counted and reported in `SchemaReport`.
4. **Money conservation** — `total_income − total_spend == net_savings` (within rounding).
5. **No division by zero** — savings rate, CoV, cadence, percentages all guarded.
6. **Privacy** — only `description_clean` / compact summaries leave the process; raw bytes
   never persisted; DB and `.env` git-ignored.
7. **LLM-optional parity** — `LLM_PROVIDER=none` (or budget exhausted) produces a valid
   analysis with no network calls.
8. **The LLM never computes numbers** — every figure in insights/narrative/chat traces to a
   code-computed metric or tool result (assert equality in tests).
9. **Every LLM path is cached + budget-checked + has a fallback** — no uncontrolled spend; no
   hard failure when over budget or rate-limited.
10. **Determinism** — same input + rules (LLM cached) ⇒ same numbers; prose may vary, numbers must not.
11. **No `NaN`/`None`/`undefined`/`$`** ever rendered to the user.

---

## Priority Test Matrix (minimum coverage before daily use)

| Must-have (🔴) by phase | Cases |
|---|---|
| P2 ingest/clean | I2, I3, I5, I6, I7, I9, D1, D2, D5, A1, A2, A6, C1, C2, C3, C7 |
| P3 rules | R1, R2, R7 |
| P4 metrics/api | M1, M8, S1 |
| P6 recurring | RC1, RC6, RC7 |
| P7 storage | DB1, DB6 |
| P8 budget/cache | T1, T2, T3, T8 |
| P9 LLM categorization | L1, L2, L3, L4, L5, L9 |
| P10/P11 analyst | AN1, AN2, AN3, AN8 |
| privacy | P1c, P3c, P6c |
| P13 upload/formats | U1, U2, U3, U6 |
