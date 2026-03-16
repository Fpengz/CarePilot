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
