import Link from "next/link";
import { Button } from "@/components/ui/button";

export function NextActions({
  recommendations,
  links,
}: {
  recommendations: string[];
  links: { chat: string; meals: string; medications: string };
}) {
  return (
    <section className="rounded-3xl border border-border-soft bg-panel p-6 shadow-sm">
      <div className="space-y-1 mb-5 px-1">
        <p className="text-micro-label text-muted-foreground uppercase">Recommended Next Steps</p>
        <h3 className="text-xl font-semibold tracking-tight text-foreground">Next Actions</h3>
      </div>
      <div className="space-y-3">
        {recommendations.slice(0, 3).map((item) => (
          <div key={item} className="rounded-2xl bg-surface border border-border-soft px-5 py-4 text-sm text-foreground shadow-sm leading-relaxed">
            {item}
          </div>
        ))}
      </div>
      <div className="mt-8 flex flex-wrap gap-3">
        <Button asChild className="rounded-xl px-6">
          <Link href={links.chat}>Ask in chat</Link>
        </Button>
        <Button asChild variant="secondary" className="rounded-xl px-6">
          <Link href={links.meals}>Review meals</Link>
        </Button>
        <Button asChild variant="secondary" className="rounded-xl px-6">
          <Link href={links.medications}>Review meds</Link>
        </Button>
      </div>
    </section>
  );
}
