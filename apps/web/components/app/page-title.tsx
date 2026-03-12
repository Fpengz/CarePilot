import { Badge } from "@/components/ui/badge";

export function PageTitle({
  eyebrow,
  title,
  description,
  tags = [],
}: {
  eyebrow?: string;
  title: string;
  description: string;
  tags?: string[];
}) {
  return (
    <section className="mb-6 rounded-2xl border border-[color:var(--border)] bg-[color:var(--panel)] p-7 shadow-[0_18px_36px_rgba(15,23,42,0.08)] dark:shadow-[0_18px_36px_rgba(0,0,0,0.4)]">
      <div className="flex flex-wrap items-center gap-2">
        {eyebrow ? <Badge className="rounded-full px-3 py-1">{eyebrow}</Badge> : null}
        {tags.map((tag) => (
          <Badge key={tag} variant="outline" className="rounded-full px-3 py-1">
            {tag}
          </Badge>
        ))}
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <div>
          <h2 className="clinical-title">{title}</h2>
          <p className="clinical-body mt-3 max-w-[72ch] text-base">{description}</p>
        </div>
        <div className="hidden lg:flex flex-col items-end gap-2 text-xs uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
          <span>Clinical calm</span>
          <span className="h-[2px] w-16 bg-[color:var(--accent)]/50" />
        </div>
      </div>
    </section>
  );
}
