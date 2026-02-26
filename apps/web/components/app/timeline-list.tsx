import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export interface TimelineListItem {
  id: string;
  title: string;
  subtitle?: string;
  badges?: string[];
  onClick?: () => void;
}

export function TimelineList({
  title,
  description,
  items,
  emptyLabel,
}: {
  title: string;
  description?: string;
  items: TimelineListItem[];
  emptyLabel: string;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
      </CardHeader>
      <CardContent>
        {items.length > 0 ? (
          <div className="data-list">
            {items.map((item) => {
              const className = item.onClick
                ? "data-list-row w-full text-left transition hover:bg-white/80 dark:hover:bg-[color:var(--card)]"
                : "data-list-row";
              const content = (
                <>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium">{item.title}</span>
                    {(item.badges ?? []).map((badge) => (
                      <span key={badge} className="rounded-full border border-[color:var(--border)] px-2 py-1 text-xs">
                        {badge}
                      </span>
                    ))}
                  </div>
                  {item.subtitle ? <div className="app-muted break-all text-xs">{item.subtitle}</div> : null}
                </>
              );
              if (item.onClick) {
                return (
                  <button key={item.id} type="button" onClick={item.onClick} className={className}>
                    {content}
                  </button>
                );
              }
              return (
                <div key={item.id} className={className}>
                  {content}
                </div>
              );
            })}
          </div>
        ) : (
          <p className="app-muted text-sm">{emptyLabel}</p>
        )}
      </CardContent>
    </Card>
  );
}
