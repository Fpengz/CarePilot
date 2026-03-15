"use client";

import { useEffect, useRef, useState } from "react";
import { Bell, Clock, MapPin, Calendar, MoreVertical } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ReminderDefinitionApi, ReminderOccurrenceApi } from "@/lib/types";

const timestampFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

function statusTone(status: ReminderOccurrenceApi["status"]) {
  if (status === "completed" || status === "taken") return "status-chip-teal";
  if (status === "missed" || status === "skipped") return "status-chip-rose";
  if (status === "snoozed") return "status-chip-amber";
  return "status-chip-slate";
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
  const body = definition?.body ?? definition?.instructions_text ?? "Instructions";
  const time = occurrence ? timestampFormatter.format(new Date(occurrence.trigger_at)) : null;
  const schedule = scheduleSummary(definition);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const buttonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!menuOpen) return;
    function handleClick(event: MouseEvent) {
      const target = event.target as Node;
      if (menuRef.current?.contains(target) || buttonRef.current?.contains(target)) return;
      setMenuOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [menuOpen]);

  return (
    <div className="group flex items-center justify-between gap-4 glass-card !p-4 transition-all hover:bg-white/50 dark:hover:bg-black/50">
      <div className="flex items-start gap-4">
        <div className={cn(
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-white/10",
          occurrence ? (occurrence.status === "completed" || occurrence.status === "taken" ? "bg-health-teal-soft text-health-teal" : "bg-health-rose-soft text-health-rose") : "bg-health-amber-soft text-health-amber"
        )}>
          {occurrence ? <Clock className="h-5 w-5" /> : <Bell className="h-5 w-5" />}
        </div>
        
        <div className="min-w-0 space-y-1 text-left">
          <div className="text-sm font-bold tracking-tight text-[color:var(--foreground)]">{title}</div>
          <div className="text-xs text-[color:var(--muted-foreground)] line-clamp-1">{body}</div>
          <div className="flex flex-wrap items-center gap-3 pt-1">
            {time && (
              <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-60">
                <Calendar className="h-3 w-3" /> {time}
              </span>
            )}
            {!time && schedule && (
              <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-60">
                <Calendar className="h-3 w-3" /> {schedule}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex min-w-[150px] items-center justify-end gap-3">
        {occurrence ? (
          <span className={cn("status-chip", statusTone(occurrence.status))}>
            {occurrence.status}
          </span>
        ) : (
          <div className="flex items-center gap-2">
            <span className={cn("status-chip", definition?.active ? "status-chip-teal" : "status-chip-slate")}>
              {definition?.active ? "Active" : "Paused"}
            </span>
          </div>
        )}
        <div className="relative">
          <button
            ref={buttonRef}
            className="h-8 w-8 rounded-lg text-[color:var(--muted-foreground)] opacity-70 transition-opacity hover:bg-[color:var(--muted)] hover:opacity-100"
            aria-label="More options"
            aria-expanded={menuOpen}
            aria-haspopup="menu"
            onClick={() => setMenuOpen((prev) => !prev)}
            type="button"
          >
            <MoreVertical className="h-4 w-4" />
          </button>
          {menuOpen ? (
            <div
              ref={menuRef}
              className="absolute right-0 top-full z-10 mt-2 w-44 rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-1 shadow-lg"
            >
              {definition && onEdit ? (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      onEdit();
                    }}
                    className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold text-[color:var(--foreground)] hover:bg-[color:var(--muted)]"
                  >
                    Edit
                  </button>
                  {onToggle ? (
                    <button
                      type="button"
                      onClick={() => {
                        setMenuOpen(false);
                        onToggle();
                      }}
                      disabled={toggleDisabled}
                      className={cn(
                        "flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold",
                        toggleDisabled ? "text-[color:var(--muted-foreground)] opacity-60" : "text-[color:var(--foreground)] hover:bg-[color:var(--muted)]",
                      )}
                    >
                      {definition.active ? "Pause" : "Activate"}
                    </button>
                  ) : null}
                </>
              ) : null}

              {occurrence && onAction ? (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      onAction("taken");
                    }}
                    disabled={actionDisabled}
                    className={cn(
                      "flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold",
                      actionDisabled ? "text-[color:var(--muted-foreground)] opacity-60" : "text-[color:var(--foreground)] hover:bg-[color:var(--muted)]",
                    )}
                  >
                    Finished
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      onAction("skipped");
                    }}
                    disabled={actionDisabled}
                    className={cn(
                      "flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold",
                      actionDisabled ? "text-[color:var(--muted-foreground)] opacity-60" : "text-[color:var(--foreground)] hover:bg-[color:var(--muted)]",
                    )}
                  >
                    Skipped
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      onAction("snooze", 10);
                    }}
                    disabled={actionDisabled}
                    className={cn(
                      "flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold",
                      actionDisabled ? "text-[color:var(--muted-foreground)] opacity-60" : "text-[color:var(--foreground)] hover:bg-[color:var(--muted)]",
                    )}
                  >
                    Snooze 10m
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      onAction("snooze", 30);
                    }}
                    disabled={actionDisabled}
                    className={cn(
                      "flex w-full items-center justify-between rounded-lg px-3 py-2 text-xs font-semibold",
                      actionDisabled ? "text-[color:var(--muted-foreground)] opacity-60" : "text-[color:var(--foreground)] hover:bg-[color:var(--muted)]",
                    )}
                  >
                    Snooze 30m
                  </button>
                </>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
