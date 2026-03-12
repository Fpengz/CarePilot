"use client";

import Link from "next/link";

export default function BrutalistSamplePage() {
  return (
    <div
      className="min-h-screen px-6 py-10"
      style={{
        background: "#f5f2ea",
        color: "#141414",
        fontFamily: "\"Space Grotesk\", \"Source Sans 3\", sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
      `}</style>
      <div className="mx-auto max-w-6xl space-y-12">
        <header className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-3 border-2 border-black px-3 py-1 text-xs uppercase tracking-[0.3em]">
              Brutalist mode
            </div>
            <h1 className="text-5xl font-bold leading-[1.05]">
              Health guidance with zero ornament.
            </h1>
            <p className="text-base max-w-xl">
              High‑contrast blocks, thick borders, and direct labels. The interface is
              blunt and fast—built for decisions.
            </p>
          </div>
          <div className="border-2 border-black bg-[#fff45b] p-6 shadow-[8px_8px_0_#000]">
            <div className="text-xs uppercase tracking-[0.3em]">Status</div>
            <div className="mt-3 text-3xl font-bold">2 ACTIONS</div>
            <p className="mt-3 text-sm">Lunch spike detected. Sodium high. Hydration low.</p>
            <button className="mt-6 border-2 border-black bg-black px-5 py-2 text-xs uppercase tracking-[0.2em] text-[#fff45b]">
              REVIEW NOW
            </button>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-4">
            <div className="border-2 border-black bg-white p-5">
              <div className="text-xs uppercase tracking-[0.28em]">Case summary</div>
              <p className="mt-3 text-sm">
                Post‑lunch glucose spike. Medication adherence stable. One swap required.
              </p>
            </div>
            <div className="border-2 border-black bg-white p-5">
              <div className="text-xs uppercase tracking-[0.28em]">Signals</div>
              <ul className="mt-3 space-y-2 text-sm">
                <li>GLUCOSE +18%</li>
                <li>SODIUM 900mg</li>
                <li>WATER ‑350ml</li>
              </ul>
            </div>
          </div>
          <div className="border-2 border-black bg-white p-6">
            <div className="text-xs uppercase tracking-[0.28em]">Interventions</div>
            <div className="mt-4 space-y-4">
              {[
                "Swap fried noodles → soup noodles",
                "Hydration reminder @ 14:00",
                "Evening check‑in prompt",
              ].map((item) => (
                <div key={item} className="border-2 border-black px-4 py-3 text-sm">
                  {item}
                </div>
              ))}
            </div>
            <Link href="/style-samples" className="mt-6 inline-block text-xs uppercase tracking-[0.2em]">
              Back to samples →
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
