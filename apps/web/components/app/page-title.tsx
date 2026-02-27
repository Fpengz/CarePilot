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
    <div className="mb-5 rounded-2xl border border-[color:var(--border)] bg-white/55 p-4 text-center shadow-[0_8px_24px_rgba(18,20,16,0.04)] backdrop-blur-sm dark:bg-[color:var(--panel-soft)] sm:text-left md:mb-6 md:p-5">
      <div className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
        {eyebrow ? <Badge>{eyebrow}</Badge> : null}
        {tags.map((tag) => (
          <Badge key={tag} variant="outline">
            {tag}
          </Badge>
        ))}
      </div>
      <div className="mt-3">
        <h2 className="text-[1.75rem] font-semibold leading-tight sm:text-3xl md:text-4xl">{title}</h2>
        <p className="mx-auto mt-2 max-w-[72ch] text-sm leading-6 text-[color:var(--muted-foreground)] sm:mx-0 md:text-base">
          {description}
        </p>
      </div>
      <div className="mx-auto mt-4 h-px w-full bg-gradient-to-r from-[color:var(--border)] via-[color:var(--accent)]/20 to-transparent sm:mx-0" />
    </div>
  );
}
