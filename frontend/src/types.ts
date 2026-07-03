// TypeScript mirrors of the backend Pydantic schemas (app/models/schemas.py).

export type Direction = "debit" | "credit";

export interface Transaction {
  id: string;
  date: string; // ISO date "YYYY-MM-DD"
  description_raw: string;
  description_clean: string;
  amount: number;
  direction: Direction;
  category: string;
  category_source: "rule" | "llm" | "default";
  confidence: number;
  is_recurring: boolean;
  recurring_group_id: string | null;
}

export interface RecurringGroup {
  id: string;
  merchant: string;
  cadence: string;
  typical_amount: number;
  occurrences: number;
  category: string;
}

export interface Metrics {
  total_income: number;
  total_spend: number;
  net_savings: number;
  savings_rate: number;
  top_categories: [string, number][];
  biggest_transaction: Transaction | null;
  by_month: Record<string, number>;
}

export interface Analysis {
  session_id: string;
  created_at: string;
  transactions: Transaction[];
  recurring: RecurringGroup[];
  metrics: Metrics;
  insights: string[];
  narrative?: string | null;
}

export interface SchemaReport {
  detected_columns: Record<string, string | null>;
  total_rows: number;
  parsed_rows: number;
  dropped_rows: number;
  confidence: number;
  warnings: string[];
}

export interface UploadResponse {
  session_id: string;
  analysis: Analysis;
  schema_report: SchemaReport;
}
