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

  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: APP_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);

  const bucket: Record<string, string> = {};
  for (const part of parts) {
    if (part.type !== "literal") bucket[part.type] = part.value;
  }
  if (!bucket.year || !bucket.month || !bucket.day) return String(value);
  return `${bucket.year}-${bucket.month}-${bucket.day}`;
}

export function parseDateKey(dateKey: string): Date | null {
  const [year, month, day] = dateKey.split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(Date.UTC(year, month - 1, day));
}
