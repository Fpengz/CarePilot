import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function JsonViewer({
  title,
  description,
  data,
  emptyLabel = "No data yet.",
}: {
  title: string;
  description?: string;
  data: unknown;
  emptyLabel?: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>
        {data ? (
          <pre className="app-code">{JSON.stringify(data, null, 2)}</pre>
        ) : (
          <div className="rounded-xl border border-dashed border-[color:var(--border)] bg-white/40 p-4 text-sm text-[color:var(--muted-foreground)] dark:bg-[color:var(--panel-soft)]/70">
            {emptyLabel}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
