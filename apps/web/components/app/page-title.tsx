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
    <div className="mb-6 rounded-2xl border border-[color:var(--border)] bg-[color:var(--panel)] p-5 shadow-[0_18px_50px_rgba(18,24,20,0.08)]">
      <div className="flex flex-wrap items-center gap-2">
        {eyebrow ? <Badge>{eyebrow}</Badge> : null}
        {tags.map((tag) => (
          <Badge key={tag} variant="outline">
            {tag}
          </Badge>
        ))}
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <div>
          <h2 className="text-[2rem] font-semibold leading-[1.05] tracking-[-0.02em] sm:text-4xl">
            {title}
          </h2>
          <p className="mt-3 max-w-[72ch] text-sm leading-6 text-[color:var(--muted-foreground)] sm:text-base">
            {description}
          </p>
        </div>
        <div className="hidden lg:flex flex-col items-end gap-2 text-xs uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
          <span>Companion signal</span>
          <span className="h-[2px] w-16 bg-[color:var(--accent)]/40" />
        </div>
      </div>
    </div>
  );
}
