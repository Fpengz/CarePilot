import { cn } from "@/lib/utils";

export function HealthSignal({ metabolic, risk }: { metabolic: string; risk: string }) {
  return (
    <div className="glass-card flex flex-col justify-between h-full">
      <div className="text-xs font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Health Signal</div>
      <div className="mt-4 flex flex-wrap gap-2">
        <span className="status-chip bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">Metabolic: {metabolic}</span>
        <span className="status-chip bg-slate-500/10 text-slate-600 dark:text-slate-400">Risk: {risk}</span>
      </div>
    </div>
  );
}
