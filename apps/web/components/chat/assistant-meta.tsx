export function AssistantMeta({
  kindLabel,
  confidence,
}: {
  kindLabel?: string;
  confidence?: number;
}) {
  if (!kindLabel && confidence === undefined) return null;
  return (
    <div className="flex flex-wrap items-center gap-3 text-xs text-[color:var(--muted-foreground)]">
      {kindLabel ? (
        <span className="uppercase tracking-[0.2em]">{kindLabel}</span>
      ) : null}
      {confidence !== undefined ? (
        <span className="tabular-nums">
          {Math.round(confidence * 100)}% confidence
        </span>
      ) : null}
    </div>
  );
}
