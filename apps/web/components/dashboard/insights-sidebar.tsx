import { AlertCircle } from "lucide-react";

export function InsightsSidebar({ recommendation }: { recommendation: string }) {
  return (
    <div className="glass-card h-full !bg-transparent border-none shadow-none flex flex-col justify-center !p-0">
      <div className="border-l-2 border-health-amber pl-4 py-1">
        <div className="flex items-center gap-2 text-health-amber mb-2">
          <AlertCircle className="h-3.5 w-3.5" />
          <span className="text-[9px] font-bold uppercase tracking-[0.2em]">Action Insight</span>
        </div>
        <p className="text-sm font-semibold leading-relaxed text-[color:var(--foreground)]">
          {recommendation}
        </p>
      </div>
    </div>
  );
}
