import { useState } from "react";
import type { UploadResponse } from "../types";
import SummaryCards from "../components/SummaryCards";
import CategoryChart from "../components/CategoryChart";
import InsightsPanel from "../components/InsightsPanel";
import NarrativePanel from "../components/NarrativePanel";
import RecurringTable from "../components/RecurringTable";
import TransactionTable from "../components/TransactionTable";

export default function Dashboard({ data }: { data: UploadResponse }) {
  const { analysis, schema_report } = data;
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  const handleDownload = async (format: "csv" | "pdf" | "html") => {
    setDropdownOpen(false);
    setPdfError(null);

    const url = `/api/report/${analysis.session_id}?format=${format}`;

    if (format === "html") {
      window.open(url, "_blank");
      return;
    }

    if (format === "csv") {
      window.location.href = url;
      return;
    }

    // PDF requires special error handling for WeasyPrint/Cairo dependencies on Windows host
    setPdfLoading(true);
    try {
      const response = await fetch(url);
      if (!response.ok) {
        const errBody = await response.json();
        throw new Error(errBody.detail || "Failed to download PDF.");
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.setAttribute("download", `rupeeradar_report_${analysis.session_id.substring(0, 8)}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err: any) {
      console.error(err);
      setPdfError(err.message || "PDF engine is offline. Please use the HTML Print version option.");
    } finally {
      setPdfLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {pdfError && (
        <div className="rounded-xl bg-amber-50 p-4 text-xs text-amber-800 ring-1 ring-amber-200 flex items-start gap-2.5 shadow-sm animate-fade-in">
          <span className="text-sm">⚠️</span>
          <div>
            <strong className="font-semibold block mb-0.5">PDF Export Fallback</strong>
            {pdfError}
          </div>
        </div>
      )}

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-xl bg-white px-4 py-3 text-xs text-slate-500 ring-1 ring-slate-200 shadow-sm">
        <div>
          Parsed <strong className="text-slate-700">{schema_report.parsed_rows}</strong> of{" "}
          {schema_report.total_rows} rows
          {schema_report.dropped_rows > 0 && ` · ${schema_report.dropped_rows} non-transaction rows skipped`}
          {schema_report.warnings.length > 0 && ` · ${schema_report.warnings.length} warning(s)`}
        </div>

        <div className="relative">
          <button
            onClick={() => setDropdownOpen(!dropdownOpen)}
            disabled={pdfLoading}
            className="flex items-center gap-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 disabled:bg-slate-50 font-semibold px-3 py-1.5 text-slate-700 transition-colors shadow-sm"
          >
            {pdfLoading ? "⏳ Generating PDF..." : "📥 Export Report"}
            <span className="text-[9px] text-slate-400">▼</span>
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 mt-1.5 w-44 rounded-xl bg-white py-1 shadow-lg ring-1 ring-black/5 z-20 border border-slate-100">
              <button
                onClick={() => handleDownload("csv")}
                className="w-full text-left px-4 py-2 text-xs hover:bg-slate-50 text-slate-700 font-semibold transition-colors"
              >
                CSV Spreadsheet
              </button>
              <button
                onClick={() => handleDownload("pdf")}
                className="w-full text-left px-4 py-2 text-xs hover:bg-slate-50 text-slate-700 font-semibold transition-colors"
              >
                PDF Report
              </button>
              <button
                onClick={() => handleDownload("html")}
                className="w-full text-left px-4 py-2 text-xs hover:bg-slate-50 text-indigo-600 font-bold transition-colors border-t border-slate-100"
              >
                HTML Print Version
              </button>
            </div>
          )}
        </div>
      </div>

      <SummaryCards metrics={analysis.metrics} />

      <NarrativePanel narrative={analysis.narrative} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <CategoryChart metrics={analysis.metrics} />
        <InsightsPanel insights={analysis.insights} />
      </div>

      <RecurringTable recurring={analysis.recurring} />

      <TransactionTable transactions={analysis.transactions} />
    </div>
  );
}
