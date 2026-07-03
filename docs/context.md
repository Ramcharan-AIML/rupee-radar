# RupeeRadar — Project Context

> AI-powered personal finance assistant that turns messy bank statement data into clear,
> human-readable spending insights.

---

## 1. Problem & Goal

Working professionals make hundreds of monthly transactions (UPI, cards, bank transfers,
subscriptions, EMIs, rent, shopping, food delivery, travel, investments). Bank statements
hold all this data, but the transaction descriptions are **messy, inconsistent, and hard to
categorize manually**.

**Goal:** Build an end-to-end solution that converts raw financial transaction data into
meaningful personal finance insights, helping users understand *where their money is going*.

### Key questions the product must answer
- What are my biggest spending categories?
- How much did I spend this month?
- Which transactions are recurring subscriptions or EMIs?
- What was my biggest transaction?
- What are the top insights from my spending behavior?

---

## 2. Core Requirements

1. **Accept** bank statement data as input.
2. **Extract / clean** transactions into a structured format.
3. **Categorize** transactions into meaningful groups:
   `Food, Travel, Shopping, Bills, EMI, Subscriptions, Salary, Rent, Investments, Other`.
4. **Detect recurring** transactions (subscriptions, EMIs, rent, SIPs, insurance).
5. **Compute key metrics:** total income, total spend, savings, top categories,
   biggest transactions.
6. **Generate insights** — clear, human-readable, using *actual transaction amounts*.
7. **Present** results via a simple UI / dashboard / downloadable report.

---

## 3. Expected Deliverables

A working prototype that demonstrates:
- Cleaned transaction data
- Categorized expenses
- Recurring payment detection
- Spend summary dashboard
- **At least three** personalized financial insights
- A final shareable report or visual summary

**Final deliverable:** a deployed or locally runnable app that takes raw bank statement
data and produces a clear personal finance summary.

---

## 4. Evaluation Criteria

| Criterion | What it means |
|---|---|
| Categorization accuracy | Cleaning + classifying messy descriptions correctly |
| Insight quality | Insights are useful, specific, and amount-backed |
| Real-world robustness | Handles messy, inconsistent transaction text |
| UX | Simple and useful to a non-technical user |
| Completeness | Full end-to-end workflow works |
| Privacy | Privacy-conscious handling of sensitive financial data |

---

## 5. Constraints & Guidance

- **Prioritize a working end-to-end prototype** over perfect support for every bank format.
- Tech stack and implementation approach are **free to choose**.
- Treat financial data as **sensitive** — be privacy-conscious throughout.

---

## 6. Suggested Pipeline (reference architecture)

```
Raw statement (CSV/PDF/Excel)
        │
        ▼
 [1] Ingest & parse        → load file, detect columns (date, description, amount, type)
        │
        ▼
 [2] Clean & normalize     → standardize dates/amounts, strip noise from descriptions
        │
        ▼
 [3] Categorize            → rules/keywords + ML/LLM fallback → category per txn
        │
        ▼
 [4] Recurring detection   → group by merchant + cadence (monthly/weekly) + stable amount
        │
        ▼
 [5] Metrics & insights    → totals, savings, top categories, biggest txn, 3+ insights
        │
        ▼
 [6] Present               → dashboard + downloadable report
```

---

## 7. Categories (canonical list)

`Food` · `Travel` · `Shopping` · `Bills` · `EMI` · `Subscriptions` · `Salary` · `Rent` ·
`Investments` · `Other`

---

## 8. Project Status

- **Stage:** Inception — only the problem statement exists ([docs/problemStatement.txt](docs/problemStatement.txt)).
- **Repo:** not yet a git repository.
- **Stack:** not yet chosen.
- **Working directory:** `RupeeRadar_project`

### Open decisions (TBD)
- Input formats to support first (CSV vs PDF vs Excel)
- Tech stack (e.g., Python + pandas + Streamlit/Flask, or JS)
- Categorization method (rule-based, ML, or LLM-assisted)
- Local-only vs deployed; how sensitive data is stored/processed

---

_Source of truth for requirements: [docs/problemStatement.txt](docs/problemStatement.txt)._
