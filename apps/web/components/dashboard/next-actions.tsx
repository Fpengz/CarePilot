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
    <section className="px-2 space-y-6">
      <div className="space-y-1">
        <p className="text-micro-label text-muted-foreground uppercase font-bold tracking-widest">Recommended Path</p>
        <h3 className="text-xl font-semibold tracking-tight text-foreground">Next Actions</h3>
      </div>
      <div className="space-y-4">
        {recommendations.slice(0, 3).map((item) => (
          <div key={item} className="rounded-2xl bg-surface border border-border-soft px-6 py-5 text-sm text-foreground shadow-sm leading-relaxed border-l-4 border-l-accent-teal">
            {item}
          </div>
        ))}
      </div>
      <div className="pt-4 flex flex-col gap-3">
        <Button asChild className="rounded-2xl h-12 w-full font-bold shadow-lg shadow-accent-teal/20">
          <Link href={links.chat}>Inquire in Clinical Chat</Link>
        </Button>
        <div className="grid grid-cols-2 gap-3">
          <Button asChild variant="secondary" className="rounded-xl h-11 text-xs">
            <Link href={links.meals}>Meal Logs</Link>
          </Button>
          <Button asChild variant="secondary" className="rounded-xl h-11 text-xs">
            <Link href={links.medications}>Medication</Link>
          </Button>
        </div>
      </div>
    </section>
  );
}
