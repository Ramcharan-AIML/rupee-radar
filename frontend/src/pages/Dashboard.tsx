import type { UploadResponse } from "../types";
import SummaryCards from "../components/SummaryCards";
import CategoryChart from "../components/CategoryChart";
import InsightsPanel from "../components/InsightsPanel";
import RecurringTable from "../components/RecurringTable";
import TransactionTable from "../components/TransactionTable";

export default function Dashboard({ data }: { data: UploadResponse }) {
  const { analysis, schema_report } = data;

  return (
    <div className="space-y-6">
      <div className="rounded-xl bg-white px-4 py-2 text-xs text-slate-500 ring-1 ring-slate-200">
        Parsed <strong className="text-slate-700">{schema_report.parsed_rows}</strong> of{" "}
        {schema_report.total_rows} rows
        {schema_report.dropped_rows > 0 && ` · ${schema_report.dropped_rows} non-transaction rows skipped`}
        {schema_report.warnings.length > 0 && ` · ${schema_report.warnings.length} warning(s)`}
      </div>

      <SummaryCards metrics={analysis.metrics} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <CategoryChart metrics={analysis.metrics} />
        <InsightsPanel insights={analysis.insights} />
      </div>

      <RecurringTable recurring={analysis.recurring} />

      <TransactionTable transactions={analysis.transactions} />
    </div>
  );
}

