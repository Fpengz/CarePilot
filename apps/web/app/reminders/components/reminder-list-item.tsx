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
  if (status === "completed") return "bg-emerald-500/10 text-emerald-600 border-emerald-200/50";
  if (status === "missed" || status === "skipped") return "bg-rose-500/10 text-rose-600 border-rose-200/50";
  if (status === "snoozed") return "bg-amber-500/10 text-amber-600 border-amber-200/50";
  return "bg-[color:var(--accent)]/5 text-[color:var(--foreground)] border-[color:var(--border-soft)]";
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
    <div className="group flex items-center justify-between gap-4 rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-4 transition-all hover:border-[color:var(--border)] hover:shadow-sm">
      <div className="flex items-start gap-4">
        <div className={cn(
          "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border",
          occurrence ? statusTone(occurrence.status) : "bg-[color:var(--accent)]/5 text-[color:var(--accent)] border-[color:var(--accent)]/10"
        )}>
          {occurrence ? <Clock className="h-5 w-5" /> : <Bell className="h-5 w-5" />}
        </div>
        
        <div className="min-w-0 space-y-1">
          <div className="text-sm font-bold tracking-tight text-[color:var(--foreground)]">{title}</div>
          <div className="text-xs text-[color:var(--muted-foreground)] line-clamp-1">{body}</div>
          <div className="flex flex-wrap items-center gap-3 pt-1">
            {time && (
              <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-60">
                <Calendar className="h-3 w-3" /> {time}
              </span>
            )}
            {definition?.timezone && (
              <span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)] opacity-60">
                <MapPin className="h-3 w-3" /> {definition.timezone}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {occurrence ? (
          <span className={cn("rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider", statusTone(occurrence.status))}>
            {occurrence.status}
          </span>
        ) : (
          <div className="flex items-center gap-2">
            <span className={cn("rounded-full border border-[color:var(--border-soft)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[color:var(--muted-foreground)]", definition?.active ? "bg-emerald-500/10 text-emerald-600 border-emerald-100" : "bg-slate-100 text-slate-400")}>
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
              {definition ? (
                <>
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      onEdit?.();
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
