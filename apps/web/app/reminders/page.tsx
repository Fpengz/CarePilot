"use client";

import type { FormEvent } from "react";
import { useEffect, useMemo, useState } from "react";

import { AsyncLabel } from "@/components/app/async-label";
import { ErrorCard } from "@/components/app/error-card";
import { PageTitle } from "@/components/app/page-title";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  actOnReminderOccurrence,
  createReminderDefinition,
  generateReminders,
  listReminderDefinitions,
  listReminderHistory,
  listReminderNotificationLogs,
  listReminderNotificationSchedules,
  listReminders,
  listUpcomingReminderOccurrences,
  patchReminderDefinition,
} from "@/lib/api/reminder-client";
import type {
  ReminderDefinitionApi,
  ReminderEventView,
  ReminderMetrics,
  ReminderNotificationLogItem,
  ReminderOccurrenceApi,
  ReminderScheduleRuleApi,
  ScheduledReminderNotificationItem,
} from "@/lib/types";

const timestampFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

const WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function MetricsCard({ metrics }: { metrics: ReminderMetrics | null }) {
  if (!metrics) {
    return <p className="app-muted text-sm">Create today’s reminders to see adherence metrics.</p>;
  }
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div className="metric-card">
        <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Reminders Sent</div>
        <div className="mt-2 text-2xl font-semibold">{metrics.reminders_sent}</div>
      </div>
      <div className="metric-card">
        <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Confirmation Rate</div>
        <div className="mt-2 text-2xl font-semibold">{(metrics.meal_confirmation_rate * 100).toFixed(1)}%</div>
      </div>
      <div className="metric-card">
        <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Taken / Yes</div>
        <div className="mt-2 text-2xl font-semibold">{metrics.meal_confirmed_yes}</div>
      </div>
      <div className="metric-card">
        <div className="text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Skipped / No</div>
        <div className="mt-2 text-2xl font-semibold">{metrics.meal_confirmed_no}</div>
      </div>
    </div>
  );
}

function scheduleSummary(definition: ReminderDefinitionApi) {
  const { schedule } = definition;
  if (schedule.pattern === "daily_fixed_times") {
    return `Daily at ${schedule.times.join(", ")}`;
  }
  if (schedule.pattern === "one_time") {
    const date = schedule.start_date ? ` on ${schedule.start_date}` : "";
    const time = schedule.times[0] ? ` at ${schedule.times[0]}` : "";
    return `One-time${date}${time}`;
  }
  if (schedule.pattern === "meal_relative") {
    const slot = schedule.meal_slot ?? "meal";
    const direction = schedule.relative_direction ?? "after";
    const offset = schedule.offset_minutes ? ` (${schedule.offset_minutes} min)` : "";
    return `${direction === "before" ? "Before" : "After"} ${slot}${offset}`;
  }
  if (schedule.pattern === "every_x_hours") {
    const anchor = schedule.times[0] ? ` starting ${schedule.times[0]}` : "";
    return `Every ${schedule.interval_hours ?? "?"} hours${anchor}`;
  }
  if (schedule.pattern === "specific_weekdays") {
    const labels = schedule.weekdays.length
      ? schedule.weekdays
          .map((day) => WEEKDAY_LABELS[day - 1])
          .filter(Boolean)
      : [];
    return `Weekdays ${labels.length ? labels.join(", ") : "scheduled days"}`;
  }
  if (schedule.pattern === "bedtime") {
    return "Before sleep";
  }
  if (schedule.pattern === "prn") {
    return `As needed${schedule.max_daily_occurrences ? `, max ${schedule.max_daily_occurrences}/day` : ""}`;
  }
  if (schedule.pattern === "temporary_course") {
    return `Temporary course${schedule.end_date ? ` until ${schedule.end_date}` : ""}`;
  }
  return "Reminder schedule";
}

function statusTone(status: ReminderOccurrenceApi["status"]) {
  if (status === "completed") return "bg-emerald-100 text-emerald-800";
  if (status === "missed" || status === "skipped") return "bg-rose-100 text-rose-800";
  if (status === "snoozed") return "bg-amber-100 text-amber-900";
  return "bg-[color:var(--accent)]/10 text-[color:var(--foreground)]";
}

export default function RemindersPage() {
  const [definitions, setDefinitions] = useState<ReminderDefinitionApi[]>([]);
  const [upcoming, setUpcoming] = useState<ReminderOccurrenceApi[]>([]);
  const [history, setHistory] = useState<ReminderOccurrenceApi[]>([]);
  const [reminders, setReminders] = useState<ReminderEventView[]>([]);
  const [metrics, setMetrics] = useState<ReminderMetrics | null>(null);
  const [selectedOccurrenceId, setSelectedOccurrenceId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loadingAction, setLoadingAction] = useState<"generate" | "refresh" | "taken" | "skipped" | "snooze10" | "snooze30" | null>(null);
  const [schedules, setSchedules] = useState<ScheduledReminderNotificationItem[]>([]);
  const [logs, setLogs] = useState<ReminderNotificationLogItem[]>([]);
  const [createLoading, setCreateLoading] = useState(false);
  const [toggleLoadingId, setToggleLoadingId] = useState<string | null>(null);

  const [draftTitle, setDraftTitle] = useState("");
  const [draftDetails, setDraftDetails] = useState("");
  const [draftNote, setDraftNote] = useState("");
  const [draftScheduleType, setDraftScheduleType] = useState<"one_time" | "daily_fixed_times" | "every_x_hours" | "specific_weekdays">("one_time");
  const [oneTimeDate, setOneTimeDate] = useState("");
  const [oneTimeTime, setOneTimeTime] = useState("");
  const [dailyTimes, setDailyTimes] = useState<string[]>(["08:00"]);
  const [everyHours, setEveryHours] = useState("8");
  const [everyHoursTime, setEveryHoursTime] = useState("08:00");
  const [weekdayTime, setWeekdayTime] = useState("08:00");
  const [weekdaySelections, setWeekdaySelections] = useState<number[]>([1, 2, 3, 4, 5]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [timezone, setTimezone] = useState(() => Intl.DateTimeFormat().resolvedOptions().timeZone ?? "Asia/Singapore");

  const definitionMap = useMemo(() => new Map(definitions.map((item) => [item.id, item])), [definitions]);
  const nextTriggerMap = useMemo(() => {
    const map = new Map<string, ReminderOccurrenceApi>();
    for (const occurrence of [...upcoming].sort((a, b) => a.trigger_at.localeCompare(b.trigger_at))) {
      if (!map.has(occurrence.reminder_definition_id)) {
        map.set(occurrence.reminder_definition_id, occurrence);
      }
    }
    return map;
  }, [upcoming]);
  const selectedOccurrence = useMemo(
    () => [...upcoming, ...history].find((item) => item.id === selectedOccurrenceId) ?? null,
    [history, selectedOccurrenceId, upcoming],
  );
  const selectedDefinition = selectedOccurrence ? definitionMap.get(selectedOccurrence.reminder_definition_id) ?? null : null;

  async function loadStructuredData() {
    const [definitionData, upcomingData, historyData, reminderData] = await Promise.all([
      listReminderDefinitions(),
      listUpcomingReminderOccurrences(),
      listReminderHistory(),
      listReminders(),
    ]);
    setDefinitions(definitionData.items);
    setUpcoming(upcomingData.items);
    setHistory(historyData.items);
    setReminders(reminderData.reminders);
    setMetrics(reminderData.metrics);
    const nextSelected = selectedOccurrenceId || upcomingData.items[0]?.id || historyData.items[0]?.id || "";
    setSelectedOccurrenceId(nextSelected);
  }

  async function loadReminderDeliveryDetails(reminderId: string) {
    const [scheduleData, logData] = await Promise.all([
      listReminderNotificationSchedules(reminderId),
      listReminderNotificationLogs(reminderId),
    ]);
    setSchedules(scheduleData.items);
    setLogs(logData.items);
  }

  function buildScheduleRule(): ReminderScheduleRuleApi | null {
    const base: ReminderScheduleRuleApi = {
      pattern: draftScheduleType,
      times: [],
      weekdays: [],
      offset_minutes: 0,
      timezone,
      as_needed: false,
      metadata: {},
    };

    if (draftScheduleType === "one_time") {
      if (!oneTimeDate || !oneTimeTime) return null;
      return {
        ...base,
        pattern: "one_time",
        times: [oneTimeTime],
        start_date: oneTimeDate,
        end_date: null,
      };
    }

    if (draftScheduleType === "daily_fixed_times") {
      const cleaned = dailyTimes.map((item) => item.trim()).filter(Boolean);
      if (cleaned.length === 0) return null;
      return {
        ...base,
        pattern: "daily_fixed_times",
        times: cleaned,
        start_date: startDate || null,
        end_date: endDate || null,
      };
    }

    if (draftScheduleType === "every_x_hours") {
      const interval = Number(everyHours);
      if (!Number.isFinite(interval) || interval <= 0) return null;
      return {
        ...base,
        pattern: "every_x_hours",
        interval_hours: interval,
        times: everyHoursTime ? [everyHoursTime] : [],
        start_date: startDate || null,
        end_date: endDate || null,
      };
    }

    if (draftScheduleType === "specific_weekdays") {
      if (!weekdayTime || weekdaySelections.length === 0) return null;
      return {
        ...base,
        pattern: "specific_weekdays",
        times: [weekdayTime],
        weekdays: [...weekdaySelections].sort((a, b) => a - b),
        start_date: startDate || null,
        end_date: endDate || null,
      };
    }

    return null;
  }

  function resetDraft() {
    setDraftTitle("");
    setDraftDetails("");
    setDraftNote("");
    setDraftScheduleType("one_time");
    setOneTimeDate("");
    setOneTimeTime("");
    setDailyTimes(["08:00"]);
    setEveryHours("8");
    setEveryHoursTime("08:00");
    setWeekdayTime("08:00");
    setWeekdaySelections([1, 2, 3, 4, 5]);
    setStartDate("");
    setEndDate("");
  }

  useEffect(() => {
    if (!selectedOccurrenceId) {
      setSchedules([]);
      setLogs([]);
      return;
    }
    void loadReminderDeliveryDetails(selectedOccurrenceId).catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [selectedOccurrenceId]);

  useEffect(() => {
    void loadStructuredData().catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  async function handleCreateReminder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!draftTitle.trim()) {
      setError("Add a reminder title before saving.");
      return;
    }
    const schedule = buildScheduleRule();
    if (!schedule) {
      setError("Fill out the schedule details so we can create the reminder.");
      return;
    }
    setCreateLoading(true);
    try {
      await createReminderDefinition({
        title: draftTitle.trim(),
        body: draftDetails.trim() || null,
        special_notes: draftNote.trim() || null,
        medication_name: "",
        dosage_text: "",
        schedule,
        timezone,
        source: "manual",
        reminder_type: "medication",
        channels: undefined,
      });
      resetDraft();
      await loadStructuredData();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setCreateLoading(false);
    }
  }

  async function runOccurrenceAction(
    action: "taken" | "skipped" | "snooze",
    loadingState: "taken" | "skipped" | "snooze10" | "snooze30",
    snoozeMinutes?: number,
  ) {
    if (!selectedOccurrenceId) return;
    setError(null);
    setLoadingAction(loadingState);
    try {
      await actOnReminderOccurrence({
        occurrenceId: selectedOccurrenceId,
        action,
        snooze_minutes: snoozeMinutes,
      });
      await loadStructuredData();
      await loadReminderDeliveryDetails(selectedOccurrenceId);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingAction(null);
    }
  }

  async function toggleDefinition(definition: ReminderDefinitionApi) {
    setError(null);
    setToggleLoadingId(definition.id);
    try {
      await patchReminderDefinition(definition.id, { active: !definition.active });
      await loadStructuredData();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setToggleLoadingId(null);
    }
  }

  return (
    <div>
      <PageTitle
        eyebrow="Reminders"
        title="Reminders"
        description="Create and manage planned reminders, then act on what’s due today."
      />

      <div className="page-grid">
        <div className="section-stack">
          {error ? <ErrorCard message={error} /> : null}
          <Card className="grain-overlay border-[color:var(--border)] bg-[color:var(--card)]">
            <CardHeader>
              <CardTitle>Create reminder</CardTitle>
              <CardDescription>Add a planned reminder. Delivery channels are configured in settings.</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="grid gap-4" onSubmit={handleCreateReminder}>
                <div className="grid gap-2">
                  <Label htmlFor="reminder-title">Title</Label>
                  <Input
                    id="reminder-title"
                    placeholder="Take Metformin 500mg"
                    value={draftTitle}
                    onChange={(event) => setDraftTitle(event.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="reminder-details">Details</Label>
                  <Textarea
                    id="reminder-details"
                    placeholder="Twice daily, after meals"
                    value={draftDetails}
                    onChange={(event) => setDraftDetails(event.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="reminder-note">Note</Label>
                  <Textarea
                    id="reminder-note"
                    placeholder="Optional note for yourself"
                    value={draftNote}
                    onChange={(event) => setDraftNote(event.target.value)}
                  />
                </div>
                <div className="grid gap-3 rounded-[1rem] border border-[color:var(--border)] bg-[color:var(--card)]/70 p-3">
                  <div className="grid gap-2">
                    <Label htmlFor="reminder-schedule-type">Schedule type</Label>
                    <Select
                      id="reminder-schedule-type"
                      value={draftScheduleType}
                      onChange={(event) => setDraftScheduleType(event.target.value as typeof draftScheduleType)}
                    >
                      <option value="one_time">One-time</option>
                      <option value="daily_fixed_times">Daily fixed times</option>
                      <option value="every_x_hours">Every X hours</option>
                      <option value="specific_weekdays">Specific weekdays</option>
                    </Select>
                  </div>

                  {draftScheduleType === "one_time" ? (
                    <div className="grid gap-3 sm:grid-cols-2">
                      <label className="grid gap-2 text-sm">
                        <span className="font-medium text-[color:var(--foreground)]">Date</span>
                        <Input type="date" value={oneTimeDate} onChange={(event) => setOneTimeDate(event.target.value)} />
                      </label>
                      <label className="grid gap-2 text-sm">
                        <span className="font-medium text-[color:var(--foreground)]">Time</span>
                        <Input type="time" value={oneTimeTime} onChange={(event) => setOneTimeTime(event.target.value)} />
                      </label>
                    </div>
                  ) : null}

                  {draftScheduleType === "daily_fixed_times" ? (
                    <div className="grid gap-3">
                      {dailyTimes.map((time, index) => (
                        <div key={`${index}-${time}`} className="flex flex-wrap items-center gap-2">
                          <Input
                            type="time"
                            value={time}
                            onChange={(event) =>
                              setDailyTimes((current) => current.map((item, idx) => (idx === index ? event.target.value : item)))
                            }
                          />
                          {dailyTimes.length > 1 ? (
                            <button
                              type="button"
                              className="text-xs font-medium text-[color:var(--muted-foreground)]"
                              onClick={() => setDailyTimes((current) => current.filter((_, idx) => idx !== index))}
                            >
                              Remove
                            </button>
                          ) : null}
                        </div>
                      ))}
                      <button
                        type="button"
                        className="text-xs font-semibold text-[color:var(--accent)]"
                        onClick={() => setDailyTimes((current) => [...current, ""])}
                      >
                        Add time
                      </button>
                    </div>
                  ) : null}

                  {draftScheduleType === "every_x_hours" ? (
                    <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                      <label className="grid gap-2 text-sm">
                        <span className="font-medium text-[color:var(--foreground)]">Every</span>
                        <Input
                          type="number"
                          min={1}
                          value={everyHours}
                          onChange={(event) => setEveryHours(event.target.value)}
                        />
                        <span className="text-xs text-[color:var(--muted-foreground)]">Hours between reminders</span>
                      </label>
                      <label className="grid gap-2 text-sm">
                        <span className="font-medium text-[color:var(--foreground)]">Start time</span>
                        <Input type="time" value={everyHoursTime} onChange={(event) => setEveryHoursTime(event.target.value)} />
                      </label>
                    </div>
                  ) : null}

                  {draftScheduleType === "specific_weekdays" ? (
                    <div className="grid gap-3">
                      <div className="grid gap-2">
                        <span className="text-sm font-medium text-[color:var(--foreground)]">Weekdays</span>
                        <div className="flex flex-wrap gap-2">
                          {WEEKDAY_LABELS.map((label, index) => {
                            const value = index + 1;
                            const active = weekdaySelections.includes(value);
                            return (
                              <button
                                key={label}
                                type="button"
                                className={[
                                  "rounded-full border px-3 py-1 text-xs font-medium",
                                  active
                                    ? "border-[color:var(--accent)] bg-[color:var(--accent)]/15 text-[color:var(--foreground)]"
                                    : "border-[color:var(--border)] text-[color:var(--muted-foreground)]",
                                ].join(" ")}
                                onClick={() =>
                                  setWeekdaySelections((current) =>
                                    current.includes(value)
                                      ? current.filter((day) => day !== value)
                                      : [...current, value],
                                  )
                                }
                              >
                                {label}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                      <label className="grid gap-2 text-sm">
                        <span className="font-medium text-[color:var(--foreground)]">Time</span>
                        <Input type="time" value={weekdayTime} onChange={(event) => setWeekdayTime(event.target.value)} />
                      </label>
                    </div>
                  ) : null}

                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="grid gap-2 text-sm">
                      <span className="font-medium text-[color:var(--foreground)]">Start date (optional)</span>
                      <Input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
                    </label>
                    <label className="grid gap-2 text-sm">
                      <span className="font-medium text-[color:var(--foreground)]">End date (optional)</span>
                      <Input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
                    </label>
                  </div>

                  <label className="grid gap-2 text-sm">
                    <span className="font-medium text-[color:var(--foreground)]">Timezone</span>
                    <Input value={timezone} onChange={(event) => setTimezone(event.target.value)} />
                  </label>
                </div>

                <div className="flex flex-wrap gap-2">
                  <Button type="submit" disabled={createLoading}>
                    <AsyncLabel active={createLoading} loading="Saving" idle="Create reminder" />
                  </Button>
                  <Button type="button" variant="secondary" disabled={createLoading} onClick={resetDraft}>
                    Reset
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Planned reminders</CardTitle>
              <CardDescription>Reminder definitions with schedules and next triggers.</CardDescription>
            </CardHeader>
            <CardContent>
              {definitions.length > 0 ? (
                <div className="data-list">
                  {definitions.map((definition) => {
                    const nextOccurrence = nextTriggerMap.get(definition.id);
                    return (
                      <div key={definition.id} className="data-list-row gap-3">
                        <div className="min-w-0 space-y-1">
                          <div className="text-sm font-medium">{definition.title}</div>
                          <div className="text-xs text-[color:var(--muted-foreground)]">
                            {definition.body ?? definition.instructions_text ?? `${definition.medication_name} ${definition.dosage_text}`}
                          </div>
                          <div className="flex flex-wrap gap-2 text-xs text-[color:var(--muted-foreground)]">
                            <span>{scheduleSummary(definition)}</span>
                            <span>{definition.timezone}</span>
                            <span>
                              {nextOccurrence
                                ? `Next: ${timestampFormatter.format(new Date(nextOccurrence.trigger_at))}`
                                : "No upcoming occurrences"}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="rounded-full border border-[color:var(--border)] px-2 py-1 text-xs">
                            {definition.active ? "active" : "paused"}
                          </span>
                          <Button
                            variant="secondary"
                            size="sm"
                            disabled={toggleLoadingId === definition.id}
                            onClick={() => void toggleDefinition(definition)}
                          >
                            {definition.active ? "Pause" : "Activate"}
                          </Button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="app-muted text-sm">No planned reminders yet. Create one above.</p>
              )}
            </CardContent>
          </Card>

          <details className="rounded-[1.25rem] border border-[color:var(--border)] bg-[color:var(--card)] p-4">
            <summary className="flex cursor-pointer items-center justify-between text-sm font-semibold text-[color:var(--foreground)]">
              Upcoming & history
              <span className="text-xs font-normal text-[color:var(--muted-foreground)]">Expand</span>
            </summary>
            <div className="mt-4 space-y-4">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Upcoming reminders</CardTitle>
                  <CardDescription>Actionable reminder occurrences sorted by next trigger time.</CardDescription>
                </CardHeader>
                <CardContent>
                  {upcoming.length > 0 ? (
                    <div className="data-list">
                      {upcoming.map((occurrence) => {
                        const active = selectedOccurrenceId === occurrence.id;
                        const definition = definitionMap.get(occurrence.reminder_definition_id);
                        return (
                          <button
                            key={occurrence.id}
                            type="button"
                            onClick={() => setSelectedOccurrenceId(occurrence.id)}
                            className={[
                              "w-full rounded-[1rem] border px-3 py-3 text-left transition",
                              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--ring)] focus-visible:ring-offset-2",
                              "focus-visible:ring-offset-[color:var(--background)]",
                              active ? "border-[color:var(--accent)] bg-[color:var(--accent)]/10" : "border-[color:var(--border)] bg-white/60 hover:bg-white/80 dark:bg-[color:var(--panel-soft)] dark:hover:bg-[color:var(--card)]",
                            ].join(" ")}
                          >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                              <div className="min-w-0 space-y-1">
                                <div className="text-sm font-medium">{definition?.title ?? "Reminder occurrence"}</div>
                                <div className="text-xs text-[color:var(--muted-foreground)]">
                                  {definition?.body ?? definition?.instructions_text ?? "Structured occurrence"}
                                </div>
                                <div className="text-xs text-[color:var(--muted-foreground)]">
                                  {timestampFormatter.format(new Date(occurrence.trigger_at))}
                                </div>
                              </div>
                              <span className={`rounded-full px-2 py-1 text-xs font-medium ${statusTone(occurrence.status)}`}>
                                {occurrence.status}
                              </span>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="app-muted text-sm">No upcoming occurrences queued yet.</p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Recent history</CardTitle>
                  <CardDescription>Completed, skipped, snoozed, and missed reminder outcomes.</CardDescription>
                </CardHeader>
                <CardContent>
                  {history.length > 0 ? (
                    <div className="data-list">
                      {history.map((occurrence) => {
                        const definition = definitionMap.get(occurrence.reminder_definition_id);
                        return (
                          <div key={occurrence.id} className="data-list-row gap-3">
                            <div className="min-w-0 space-y-1">
                              <div className="text-sm font-medium">{definition?.title ?? "Reminder occurrence"}</div>
                              <div className="text-xs text-[color:var(--muted-foreground)]">
                                {occurrence.action ? `${occurrence.action} · ` : ""}
                                {timestampFormatter.format(new Date(occurrence.acted_at ?? occurrence.updated_at))}
                              </div>
                            </div>
                            <span className={`rounded-full px-2 py-1 text-xs font-medium ${statusTone(occurrence.status)}`}>
                              {occurrence.status}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="app-muted text-sm">No reminder history yet.</p>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Legacy reminder events</CardTitle>
                  <CardDescription>Compatibility projection retained during the structured reminder migration.</CardDescription>
                </CardHeader>
                <CardContent>
                  {reminders.length > 0 ? (
                    <div className="data-list">
                      {reminders.map((reminder) => (
                        <div key={reminder.id} className="data-list-row sm:flex-row sm:items-center sm:justify-between">
                          <div className="min-w-0">
                            <div className="text-sm font-medium">{reminder.title}</div>
                            <div className="text-xs text-[color:var(--muted-foreground)]">
                              {reminder.body ?? "Reminder"} · {timestampFormatter.format(new Date(reminder.scheduled_at))}
                            </div>
                          </div>
                          <div className="flex flex-wrap gap-2 text-xs">
                            <span className="rounded-full border border-[color:var(--border)] px-2 py-1">{reminder.reminder_type}</span>
                            <span className="rounded-full border border-[color:var(--border)] px-2 py-1">{reminder.status}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="app-muted text-sm">No legacy reminder events loaded yet.</p>
                  )}
                </CardContent>
              </Card>
            </div>
          </details>
        </div>

        <div className="section-stack">
          <Card className="grain-overlay border-[color:var(--border)] bg-[color:var(--card)]">
            <CardHeader>
              <CardTitle>Today’s reminders</CardTitle>
              <CardDescription>Create today’s reminders from planned schedules, then act on what’s due.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="flex flex-wrap gap-2">
                <Button
                  disabled={loadingAction !== null}
                  onClick={async () => {
                    setError(null);
                    setLoadingAction("generate");
                    try {
                      const generated = await generateReminders();
                      setReminders(generated.reminders);
                      setMetrics(generated.metrics);
                      await loadStructuredData();
                    } catch (e) {
                      setError(e instanceof Error ? e.message : String(e));
                    } finally {
                      setLoadingAction(null);
                    }
                  }}
                >
                  <AsyncLabel active={loadingAction === "generate"} loading="Creating" idle="Create today’s reminders" />
                </Button>
                <Button
                  variant="secondary"
                  disabled={loadingAction !== null}
                  onClick={async () => {
                    setError(null);
                    setLoadingAction("refresh");
                    try {
                      await loadStructuredData();
                    } catch (e) {
                      setError(e instanceof Error ? e.message : String(e));
                    } finally {
                      setLoadingAction(null);
                    }
                  }}
                >
                  <AsyncLabel active={loadingAction === "refresh"} loading="Refreshing" idle="Reload reminders" />
                </Button>
              </div>

              {selectedOccurrence ? (
                <div className="rounded-[1.25rem] border border-[color:var(--border)] bg-[linear-gradient(145deg,color-mix(in_oklab,var(--accent)_12%,white),transparent)] p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-2">
                      <div className="text-xs uppercase tracking-[0.28em] text-[color:var(--muted-foreground)]">Selected reminder</div>
                      <div className="text-lg font-semibold">{selectedDefinition?.title ?? "Reminder"}</div>
                      <div className="text-sm text-[color:var(--muted-foreground)]">
                        {selectedDefinition?.body ?? selectedDefinition?.instructions_text ?? "Details not available."}
                      </div>
                      <div className="flex flex-wrap gap-2 text-xs text-[color:var(--muted-foreground)]">
                        <span>{timestampFormatter.format(new Date(selectedOccurrence.trigger_at))}</span>
                        <span>Grace {selectedOccurrence.grace_window_minutes}m</span>
                        <span>{selectedDefinition ? scheduleSummary(selectedDefinition) : "Reminder schedule"}</span>
                      </div>
                    </div>
                    <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusTone(selectedOccurrence.status)}`}>
                      {selectedOccurrence.status}
                    </span>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <Button disabled={loadingAction !== null} onClick={() => void runOccurrenceAction("taken", "taken")}>
                      <AsyncLabel active={loadingAction === "taken"} loading="Saving" idle="Taken" />
                    </Button>
                    <Button variant="secondary" disabled={loadingAction !== null} onClick={() => void runOccurrenceAction("skipped", "skipped")}>
                      <AsyncLabel active={loadingAction === "skipped"} loading="Saving" idle="Skipped" />
                    </Button>
                    <Button variant="secondary" disabled={loadingAction !== null} onClick={() => void runOccurrenceAction("snooze", "snooze10", 10)}>
                      <AsyncLabel active={loadingAction === "snooze10"} loading="Snoozing" idle="Snooze 10m" />
                    </Button>
                    <Button variant="secondary" disabled={loadingAction !== null} onClick={() => void runOccurrenceAction("snooze", "snooze30", 30)}>
                      <AsyncLabel active={loadingAction === "snooze30"} loading="Snoozing" idle="Snooze 30m" />
                    </Button>
                  </div>

                  <details className="mt-4 rounded-[1rem] border border-[color:var(--border)] bg-[color:var(--card)]/70 p-3">
                    <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">
                      Delivery details
                    </summary>
                    <div className="mt-3 space-y-4">
                      <div>
                        <div className="mb-2 text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Scheduled notifications</div>
                        {schedules.length > 0 ? (
                          <div className="data-list">
                            {schedules.map((item) => (
                              <div key={item.id} className="data-list-row sm:flex-row sm:items-center sm:justify-between">
                                <div>
                                  <div className="text-sm font-medium">{item.channel}</div>
                                  <div className="text-xs text-[color:var(--muted-foreground)]">
                                    {timestampFormatter.format(new Date(item.trigger_at))}
                                  </div>
                                </div>
                                <span className="rounded-full border border-[color:var(--border)] px-2 py-1 text-xs">{item.status}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="app-muted text-sm">No delivery rows for the selected occurrence.</p>
                        )}
                      </div>

                      <div>
                        <div className="mb-2 text-xs uppercase tracking-[0.24em] text-[color:var(--muted-foreground)]">Notification log</div>
                        {logs.length > 0 ? (
                          <div className="data-list">
                            {logs.map((log) => (
                              <div key={log.id} className="data-list-row sm:flex-row sm:items-center sm:justify-between">
                                <div>
                                  <div className="text-sm font-medium">{log.event_type}</div>
                                  <div className="text-xs text-[color:var(--muted-foreground)]">
                                    {log.channel} · {timestampFormatter.format(new Date(log.created_at))}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="app-muted text-sm">No notification log rows for the selected occurrence.</p>
                        )}
                      </div>
                    </div>
                  </details>
                </div>
              ) : (
                <div className="rounded-[1.25rem] border border-dashed border-[color:var(--border)] bg-[color:var(--card)]/60 p-4 text-sm text-[color:var(--muted-foreground)]">
                  Create today’s reminders to see what’s due.
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Metrics</CardTitle>
              <CardDescription>Legacy reminder metrics remain visible while the structured flow rolls out.</CardDescription>
            </CardHeader>
            <CardContent>
              <MetricsCard metrics={metrics} />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
