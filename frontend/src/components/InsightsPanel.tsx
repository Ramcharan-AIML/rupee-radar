export default function InsightsPanel({ insights }: { insights: string[] }) {
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <h2 className="text-sm font-semibold text-slate-700">💡 Insights</h2>
      <ul className="mt-3 space-y-3">
        {insights.map((line, i) => (
          <li
            key={i}
            className="flex gap-3 rounded-xl bg-slate-50 p-3 text-sm text-slate-700"
          >
            <span className="font-semibold text-indigo-500">{i + 1}.</span>
            <span>{line}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
