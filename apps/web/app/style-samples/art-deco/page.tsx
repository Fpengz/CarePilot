"use client";

import Link from "next/link";

export default function ArtDecoSamplePage() {
  return (
    <div
      className="min-h-screen px-6 py-10"
      style={{
        background:
          "linear-gradient(180deg, #0c1014 0%, #141a20 55%, #0b0f13 100%)",
        color: "#f6e7c8",
        fontFamily: "\"Cinzel\", \"Source Sans 3\", serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;600;700&family=Source+Sans+3:wght@400;500;600&display=swap');
      `}</style>
      <div className="mx-auto max-w-6xl space-y-12">
        <header className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-4">
            <p className="text-xs uppercase tracking-[0.32em] text-[#c9b27a]">Art Deco system</p>
            <h1 className="text-5xl leading-[1.05] font-semibold">
              Geometry, gold, and deliberate ceremony.
            </h1>
            <p
              className="text-base text-[#d9c49b] max-w-xl"
              style={{ fontFamily: "\"Source Sans 3\", sans-serif" }}
            >
              A refined clinical companion with symmetrical layout, metallic accents,
              and a ceremony‑driven hierarchy.
            </p>
          </div>
          <div className="border border-[#c9b27a] bg-[#0f141a] p-6 shadow-[0_30px_70px_rgba(0,0,0,0.45)]">
            <div className="text-xs uppercase tracking-[0.28em] text-[#c9b27a]">Signal</div>
            <div className="mt-3 text-3xl">Guidance ready</div>
            <p className="mt-3 text-sm text-[#d9c49b]">
              Two calibrated interventions awaiting confirmation.
            </p>
            <div className="mt-6 flex gap-3">
              <button className="rounded-full border border-[#c9b27a] px-5 py-2 text-xs uppercase tracking-[0.2em] text-[#c9b27a]">
                Approve
              </button>
              <button className="rounded-full bg-[#c9b27a] px-5 py-2 text-xs uppercase tracking-[0.2em] text-[#141a20]">
                Review
              </button>
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-4">
            <div className="border border-[#c9b27a] bg-[#0f141a] p-5">
              <div className="text-xs uppercase tracking-[0.28em] text-[#c9b27a]">Case note</div>
              <p
                className="mt-3 text-sm text-[#d9c49b]"
                style={{ fontFamily: "\"Source Sans 3\", sans-serif" }}
              >
                Post‑lunch spike confirmed. Adherence consistent. Recommend a single swap
                with minimal disruption.
              </p>
            </div>
            <div className="border border-[#c9b27a] bg-[#0f141a] p-5">
              <div className="text-xs uppercase tracking-[0.28em] text-[#c9b27a]">Signals</div>
              <ul className="mt-3 space-y-2 text-sm text-[#d9c49b]">
                <li>GLUCOSE +18%</li>
                <li>SODIUM 900mg</li>
                <li>HYDRATION ‑350ml</li>
              </ul>
            </div>
          </div>
          <div className="border border-[#c9b27a] bg-[#0f141a] p-6">
            <div className="text-xs uppercase tracking-[0.28em] text-[#c9b27a]">Interventions</div>
            <div className="mt-5 space-y-4">
              {[
                "Swap fried noodles → soup noodles",
                "Hydration reminder @ 14:00",
                "Evening check‑in prompt",
              ].map((item) => (
                <div key={item} className="border border-[#c9b27a] px-4 py-3 text-sm">
                  {item}
                </div>
              ))}
            </div>
            <Link href="/style-samples" className="mt-6 inline-block text-xs uppercase tracking-[0.2em] text-[#c9b27a]">
              Back to samples →
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
