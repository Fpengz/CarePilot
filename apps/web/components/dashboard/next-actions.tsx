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
    <section className="rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-5">
      <div className="text-sm font-semibold text-[color:var(--foreground)]">Next actions</div>
      <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">
        The most important next steps based on the selected window.
      </p>
      <div className="mt-4 space-y-2">
        {recommendations.slice(0, 3).map((item) => (
          <div key={item} className="rounded-xl bg-[color:var(--panel)] px-4 py-3 text-sm">
            {item}
          </div>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button asChild className="h-11">
          <Link href={links.chat}>Ask in chat</Link>
        </Button>
        <Button asChild variant="secondary" className="h-11">
          <Link href={links.meals}>Review meals</Link>
        </Button>
        <Button asChild variant="secondary" className="h-11">
          <Link href={links.medications}>Review meds</Link>
        </Button>
      </div>
    </section>
  );
}
