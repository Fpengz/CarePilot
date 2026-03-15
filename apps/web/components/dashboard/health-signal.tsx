import { cn } from "@/lib/utils";

export function HealthSignal({ metabolic, risk }: { metabolic: string; risk: string }) {
  return (
    <div className="glass-card flex flex-col justify-between h-full">
      <div className="text-xs font-bold uppercase tracking-widest text-[color:var(--muted-foreground)]">Health Signal</div>
      <div className="mt-4 flex flex-wrap gap-2">
        <span className={cn("status-chip", metabolic === "Balanced" ? "status-chip-teal" : "status-chip-amber")}>
          Metabolic: {metabolic}
        </span>
        <span className={cn("status-chip", risk === "Low" ? "status-chip-slate" : "status-chip-rose")}>
          Risk: {risk}
        </span>
      </div>
    </div>
  );
}
