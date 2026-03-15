import { AlertCircle } from "lucide-react";

export function InsightsSidebar({ recommendation }: { recommendation: string }) {
  return (
    <div className="glass-card h-full border-amber-500/30 bg-amber-500/10 shadow-[0_8px_32px_rgba(245,158,11,0.15)] flex flex-col justify-center">
      <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400 mb-3">
        <AlertCircle className="h-4 w-4" />
        <span className="text-[10px] font-bold uppercase tracking-[0.2em]">Action Insight</span>
      </div>
      <p className="text-sm font-semibold leading-relaxed text-[color:var(--foreground)] pr-4 border-l-2 border-amber-500/50 pl-4 py-1">
        {recommendation}
      </p>
    </div>
  );
}
