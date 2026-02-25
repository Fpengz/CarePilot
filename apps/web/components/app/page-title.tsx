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
    <div className="mb-4 space-y-2 md:mb-5">
      <div className="flex flex-wrap items-center gap-2">
        {eyebrow ? <Badge>{eyebrow}</Badge> : null}
        {tags.map((tag) => (
          <Badge key={tag} variant="outline">
            {tag}
          </Badge>
        ))}
      </div>
      <div>
        <h2 className="text-2xl font-semibold md:text-3xl">{title}</h2>
        <p className="mt-1 max-w-[70ch] text-sm leading-6 text-[color:var(--muted-foreground)] md:text-base">{description}</p>
      </div>
    </div>
  );
}
