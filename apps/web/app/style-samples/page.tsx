"use client";

import Link from "next/link";

export default function StyleSamplesPage() {
  return (
    <div className="app-shell space-y-8">
      <header className="space-y-2">
        <p className="section-kicker">Design explorer</p>
        <h1 className="text-3xl font-semibold">Style samples</h1>
        <p className="app-muted text-sm max-w-2xl">
          Choose a direction for the new UI. Each sample is a full-page visual system
          prototype with typography, layout rhythm, and component styling.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        {[
          { href: "/style-samples/editorial", title: "Editorial / Magazine", desc: "Structured, literate, and grounded in typography." },
          { href: "/style-samples/organic", title: "Soft Organic / Natural", desc: "Warm gradients, rounded forms, calm rhythm." },
          { href: "/style-samples/industrial", title: "Industrial / Utilitarian", desc: "Sharp grids, mono accents, no-frills clarity." },
          { href: "/style-samples/retro-futurist", title: "Retro‑Futurist", desc: "Bold contrasts, geometric glow, optimistic sci‑tech." },
          { href: "/style-samples/brutalist", title: "Brutalist / Raw", desc: "Hard blocks, loud labels, unapologetic contrast." },
          { href: "/style-samples/art-deco", title: "Art Deco / Geometric", desc: "Symmetry, metallic accents, structured glamour." },
          { href: "/style-samples/soft-pastel", title: "Soft Pastel / Minimal", desc: "Airy spacing, gentle palette, quiet clarity." },
        ].map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="app-panel p-5 hover:shadow-[0_18px_50px_rgba(18,24,20,0.14)] transition-shadow"
          >
            <div className="text-lg font-semibold">{item.title}</div>
            <p className="app-muted mt-2 text-sm">{item.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
