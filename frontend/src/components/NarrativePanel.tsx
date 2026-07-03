import { useEffect, useState } from "react";

export default function NarrativePanel({ narrative }: { narrative?: string | null }) {
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    if (!narrative) return;
    
    // Smooth typing effect to make the AI analysis feel alive
    let index = 0;
    const interval = setInterval(() => {
      setDisplayedText((prev) => prev + narrative.charAt(index));
      index++;
      if (index >= narrative.length) {
        clearInterval(interval);
      }
    }, 10); // Adjust typing speed here
    
    return () => clearInterval(interval);
  }, [narrative]);

  if (!narrative) return null;

  return (
    <div className="rounded-2xl bg-gradient-to-br from-indigo-50/50 via-white to-white p-6 shadow-sm ring-1 ring-slate-200">
      <div className="flex items-center gap-3 mb-4">
        <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-50 text-base text-indigo-600">
          📝
        </span>
        <div>
          <h2 className="text-base font-semibold text-slate-900">Monthly Narrative Briefing</h2>
          <p className="text-xs text-slate-400">Personalized analyst overview</p>
        </div>
      </div>
      
      <p className="text-sm leading-relaxed text-slate-600 whitespace-pre-wrap font-medium">
        {displayedText || narrative}
      </p>
    </div>
  );
}
