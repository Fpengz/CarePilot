import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function formatPreviewValue(value: unknown): string {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return `${value.length} item(s)`;
  }
  if (value && typeof value === "object") {
    return "Object";
  }
  return "—";
}

export function KeyValuePreview({
  title,
  description,
  entries,
  emptyLabel,
}: {
  title: string;
  description?: string;
  entries: Array<{ key: string; value: unknown }>;
  emptyLabel: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>
        {entries.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {entries.map((entry) => (
              <div key={entry.key} className="metric-card">
                <div className="text-xs uppercase tracking-wide text-[color:var(--muted-foreground)]">
                  {entry.key}
                </div>
                <div className="mt-1 break-words text-sm font-medium">{formatPreviewValue(entry.value)}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="app-muted text-sm">{emptyLabel}</p>
        )}
      </CardContent>
    </Card>
  );
}
