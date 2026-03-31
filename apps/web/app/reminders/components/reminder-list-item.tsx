import { Bell, Clock, Calendar, MoreVertical, Edit2, Play, Pause, Check, SkipForward, Timer } from "lucide-react";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/time";
import type { ReminderDefinitionApi, ReminderOccurrenceApi } from "@/lib/types";

function statusTone(status: ReminderOccurrenceApi["status"]) {
  if (status === "completed") return "bg-health-teal/10 text-health-teal border-health-teal/20";
  if (status === "missed" || status === "skipped") return "bg-health-rose/10 text-health-rose border-health-rose/20";
  if (status === "snoozed") return "bg-health-amber/10 text-health-amber border-health-amber/20";
  return "bg-muted/10 text-muted-foreground border-muted/20";
}

function scheduleSummary(definition?: ReminderDefinitionApi): string | null {
  if (!definition) return null;
  const { schedule } = definition;
  if (schedule.pattern === "daily_fixed_times") {
    return schedule.times.length ? `Daily · ${schedule.times.join(", ")}` : "Daily";
  }
  if (schedule.pattern === "one_time") {
    const date = schedule.start_date ? ` on ${schedule.start_date}` : "";
    const time = schedule.times[0] ? ` at ${schedule.times[0]}` : "";
    return `One-time${date}${time}`;
  }
  if (schedule.pattern === "every_x_hours") {
    return schedule.interval_hours ? `Every ${schedule.interval_hours}h` : "Every X hours";
  }
  if (schedule.pattern === "specific_weekdays") {
    return schedule.weekdays.length ? `Weekly · ${schedule.weekdays.join(", ")}` : "Weekly";
  }
  return "Scheduled";
}

export function ReminderListItem({ 
  definition, 
  occurrence,
  onToggle,
  toggleDisabled,
  onEdit,
  onAction,
  actionDisabled,
}: { 
  definition?: ReminderDefinitionApi;
  occurrence?: ReminderOccurrenceApi;
  onToggle?: () => void;
  toggleDisabled?: boolean;
  onEdit?: () => void;
  onAction?: (action: "taken" | "skipped" | "snooze", snoozeMinutes?: number) => void;
  actionDisabled?: boolean;
}) {
  const title = definition?.title ?? occurrence?.reminder_definition_id ?? "Reminder";
  const body = definition?.body ?? definition?.instructions_text ?? "Clinical instructions";
  const time = occurrence ? formatDateTime(occurrence.trigger_at) : null;
  const schedule = scheduleSummary(definition);

  return (
    <article className="group flex items-center justify-between gap-4 bg-panel border border-border-soft rounded-xl p-4 transition-all hover:border-accent-teal/30 shadow-sm">
      <div className="flex items-start gap-4 min-w-0">
        <div className={cn(
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border",
          occurrence 
            ? (occurrence.status === "completed" ? "bg-health-teal/5 text-health-teal border-health-teal/10" : "bg-health-rose/5 text-health-rose border-health-rose/10") 
            : "bg-accent-teal/5 text-accent-teal border-accent-teal/10"
        )}>
          {occurrence ? <Clock className="h-5 w-5" aria-hidden="true" /> : <Bell className="h-5 w-5" aria-hidden="true" />}
        </div>
        
        <div className="min-w-0 space-y-1 text-left">
          <div className="text-[13px] font-bold tracking-tight text-foreground truncate">{title}</div>
          <div className="text-[11px] font-medium text-muted-foreground line-clamp-1 opacity-80">{body}</div>
          <div className="flex flex-wrap items-center gap-3 pt-0.5">
            {(time || schedule) && (
              <span className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-muted-foreground opacity-60">
                <Calendar className="h-3 w-3" aria-hidden="true" /> {time || schedule}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex shrink-0 items-center justify-end gap-4">
        {occurrence ? (
          <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest", statusTone(occurrence.status))}>
            {occurrence.status}
          </span>
        ) : (
          <span className={cn(
            "inline-flex items-center rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest",
            definition?.active ? "bg-health-teal/10 text-health-teal border-health-teal/20" : "bg-muted/10 text-muted-foreground border-muted/20"
          )}>
            {definition?.active ? "Active" : "Paused"}
          </span>
        )}

        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button
              className="h-8 w-8 flex items-center justify-center rounded-lg text-muted-foreground opacity-60 transition-all hover:bg-surface hover:opacity-100 focus-visible:ring-2 focus-visible:ring-accent-teal/40 outline-none"
              aria-label="More options"
            >
              <MoreVertical className="h-4 w-4" />
            </button>
          </DropdownMenu.Trigger>

          <DropdownMenu.Portal>
            <DropdownMenu.Content 
              className="z-50 min-w-[160px] overflow-hidden rounded-xl border border-border-soft bg-surface p-1 shadow-xl animate-in fade-in zoom-in-95"
              sideOffset={8}
              align="end"
            >
              {definition && onEdit && (
                <>
                  <DropdownMenu.Item 
                    className="flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-foreground outline-none hover:bg-panel focus:bg-panel transition-colors"
                    onClick={onEdit}
                  >
                    <Edit2 className="h-3.5 w-3.5 opacity-60" />
                    Edit Details
                  </DropdownMenu.Item>
                  {onToggle && (
                    <DropdownMenu.Item 
                      disabled={toggleDisabled}
                      className="flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-foreground outline-none hover:bg-panel focus:bg-panel disabled:opacity-40 transition-colors"
                      onClick={onToggle}
                    >
                      {definition.active ? (
                        <>
                          <Pause className="h-3.5 w-3.5 opacity-60" />
                          Pause Schedule
                        </>
                      ) : (
                        <>
                          <Play className="h-3.5 w-3.5 opacity-60" />
                          Resume Schedule
                        </>
                      )}
                    </DropdownMenu.Item>
                  )}
                  {occurrence && <DropdownMenu.Separator className="my-1 h-px bg-border-soft" />}
                </>
              )}

              {occurrence && onAction && (
                <>
                  <DropdownMenu.Item 
                    disabled={actionDisabled}
                    className="flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-health-teal outline-none hover:bg-health-teal/5 focus:bg-health-teal/5 disabled:opacity-40 transition-colors"
                    onClick={() => onAction("taken")}
                  >
                    <Check className="h-3.5 w-3.5" />
                    Mark Finished
                  </DropdownMenu.Item>
                  <DropdownMenu.Item 
                    disabled={actionDisabled}
                    className="flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-health-rose outline-none hover:bg-health-rose/5 focus:bg-health-rose/5 disabled:opacity-40 transition-colors"
                    onClick={() => onAction("skipped")}
                  >
                    <SkipForward className="h-3.5 w-3.5" />
                    Skip Occurrence
                  </DropdownMenu.Item>
                  
                  <DropdownMenu.Sub>
                    <DropdownMenu.SubTrigger className="flex cursor-pointer items-center justify-between gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-foreground outline-none hover:bg-panel focus:bg-panel data-[state=open]:bg-panel transition-colors">
                      <div className="flex items-center gap-2">
                        <Timer className="h-3.5 w-3.5 opacity-60" />
                        Snooze
                      </div>
                      <ChevronRightIcon className="h-3 w-3 opacity-40" />
                    </DropdownMenu.SubTrigger>
                    <DropdownMenu.Portal>
                      <DropdownMenu.SubContent 
                        className="z-[60] min-w-[120px] overflow-hidden rounded-xl border border-border-soft bg-surface p-1 shadow-xl animate-in fade-in slide-in-from-left-2"
                        sideOffset={4}
                      >
                        {[10, 30, 60].map((mins) => (
                          <DropdownMenu.Item 
                            key={mins}
                            className="flex cursor-pointer items-center rounded-lg px-3 py-2 text-xs font-semibold text-foreground outline-none hover:bg-panel focus:bg-panel transition-colors"
                            onClick={() => onAction("snooze", mins)}
                          >
                            {mins} minutes
                          </DropdownMenu.Item>
                        ))}
                      </DropdownMenu.SubContent>
                    </DropdownMenu.Portal>
                  </DropdownMenu.Sub>
                </>
              )}
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </article>
  );
}

function ChevronRightIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg 
      {...props} 
      xmlns="http://www.w3.org/2000/svg" 
      width="24" 
      height="24" 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round"
    >
      <path d="m9 18 6-6-6-6" />
    </svg>
  );
}
