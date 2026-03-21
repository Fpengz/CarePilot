export const APP_TIMEZONE = process.env.NEXT_PUBLIC_APP_TIMEZONE || "Asia/Singapore";

export function formatDateTime(
  value: string | Date | number,
  options: Intl.DateTimeFormatOptions = { dateStyle: "medium", timeStyle: "short" }
): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);

  return new Intl.DateTimeFormat(undefined, {
    ...options,
    timeZone: APP_TIMEZONE,
  }).format(date);
}

export function formatDate(
  value: string | Date | number,
  options: Intl.DateTimeFormatOptions = { dateStyle: "medium" }
): string {
  return formatDateTime(value, options);
}

export function formatTime(
  value: string | Date | number,
  options: Intl.DateTimeFormatOptions = { timeStyle: "short" }
): string {
  return formatDateTime(value, options);
}

export function formatDateKey(value: string | Date | number): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);

  // Use Intl to get the date in the target timezone, then format as YYYY-MM-DD
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: APP_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  return formatter.format(date);
}

export function parseDateKey(dateKey: string): Date | null {
  const [year, month, day] = dateKey.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(Date.UTC(year, month - 1, day));
}
