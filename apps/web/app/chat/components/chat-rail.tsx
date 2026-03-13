const EMOJI: Record<string, string> = {
  happy: "😊",
  sad: "😢",
  angry: "😤",
  frustrated: "😩",
  anxious: "😰",
  neutral: "😐",
  confused: "😕",
  fearful: "😨",
};

export function ChatRail({
  lastEmotion,
  lastUserMessage,
}: {
  lastEmotion: { label: string; score: number } | null;
  lastUserMessage: string;
}) {
  return (
    <aside className="flex flex-col gap-6" aria-label="Companion signals">
      <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-raised)] p-5 shadow-[0_20px_36px_rgba(15,23,42,0.06)]">
        <div className="text-xs font-semibold uppercase tracking-[0.22em] text-[color:var(--muted-foreground)]">
          Signals & care
        </div>
        <div className="mt-4 space-y-4">
          <div>
            <div className="text-sm font-semibold text-[color:var(--foreground)]">Current tone</div>
            {lastEmotion ? (
              <div className="mt-2 flex items-center gap-2 text-sm text-[color:var(--foreground)]">
                <span>{EMOJI[lastEmotion.label] ?? "🫥"}</span>
                <span className="capitalize">{lastEmotion.label}</span>
                <span className="text-xs text-[color:var(--muted-foreground)]">
                  {Math.round(lastEmotion.score * 100)}% confidence
                </span>
              </div>
            ) : (
              <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">
                Awaiting a new emotional signal.
              </p>
            )}
          </div>
          <div>
            <div className="text-sm font-semibold text-[color:var(--foreground)]">Focus today</div>
            <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">
              Medication adherence and a lower sodium lunch.
            </p>
          </div>
          <div>
            <div className="text-sm font-semibold text-[color:var(--foreground)]">Next check-in</div>
            <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">Evening meds · 7:30 PM</p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-5 shadow-[0_16px_30px_rgba(15,23,42,0.05)]">
        <div className="text-xs font-semibold uppercase tracking-[0.22em] text-[color:var(--muted-foreground)]">
          Last user focus
        </div>
        <p className="mt-3 text-sm text-[color:var(--foreground)]">
          {lastUserMessage || "No question yet."}
        </p>
      </div>

      <div className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--panel)] p-5 shadow-[0_16px_30px_rgba(15,23,42,0.05)]">
        <div className="text-xs font-semibold uppercase tracking-[0.22em] text-[color:var(--muted-foreground)]">
          Companion posture
        </div>
        <div className="mt-3 text-sm text-[color:var(--muted-foreground)]">
          Calm, structured guidance with explainable next steps. Surfaces trends and escalations.
        </div>
      </div>
    </aside>
  );
}
