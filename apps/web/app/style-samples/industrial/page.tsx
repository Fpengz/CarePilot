"use client";

import Link from "next/link";

export default function IndustrialSamplePage() {
  return (
    <div
      className="min-h-screen px-6 py-10"
      style={{
        background:
          "linear-gradient(180deg, #f5f5f3 0%, #e9ebee 60%, #f1f2f4 100%)",
        color: "#1b1f24",
        fontFamily: "\"IBM Plex Sans\", \"Source Sans 3\", sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap');
      `}</style>
      <div className="mx-auto max-w-6xl space-y-10">
        <header className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-3">
            <p className="text-xs uppercase tracking-[0.32em] text-[#5a6570]">Industrial system</p>
            <h1 className="text-5xl leading-[1.05] font-semibold">Operational clarity for the care loop.</h1>
            <p className="text-base text-[#4a5562] max-w-xl">
              Hard edges, mono accents, and data‑first layouts for fast clinical scanning.
            </p>
          </div>
          <div className="border border-[#c9cfd7] bg-white p-5 shadow-[0_24px_50px_rgba(20,30,40,0.12)]">
            <div className="text-xs uppercase tracking-[0.28em] text-[#7a8694]">System status</div>
            <div className="mt-3 text-3xl font-semibold">Nominal</div>
            <div className="mt-4 text-xs font-mono text-[#3b4450]">
              Last sync: 10:42 AM · 2 signals pending
            </div>
            <div className="mt-6 flex gap-2">
              <button className="bg-[#1b1f24] px-4 py-2 text-xs uppercase tracking-[0.2em] text-white">
                Review
              </button>
              <button className="border border-[#1b1f24] px-4 py-2 text-xs uppercase tracking-[0.2em] text-[#1b1f24]">
                Log
              </button>
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-4">
            <div className="border border-[#c9cfd7] bg-white p-5">
              <div className="text-xs uppercase tracking-[0.28em] text-[#7a8694]">Case summary</div>
              <p className="mt-3 text-sm text-[#333c46] leading-relaxed">
                Lunch sodium risk detected. Medication adherence stable. Recommend a
                single swap, low friction, high adherence.
              </p>
            </div>
            <div className="border border-[#c9cfd7] bg-white p-5">
              <div className="text-xs uppercase tracking-[0.28em] text-[#7a8694]">Flags</div>
              <ul className="mt-3 space-y-2 text-sm text-[#333c46] font-mono">
                <li>MED: adherence=0.84</li>
                <li>MEAL: post_lunch_spike=true</li>
                <li>HYDR: deficit=350ml</li>
              </ul>
            </div>
          </div>
          <div className="border border-[#c9cfd7] bg-white p-6">
            <div className="flex items-center justify-between">
              <div className="text-xs uppercase tracking-[0.28em] text-[#7a8694]">Interventions</div>
              <span className="font-mono text-xs text-[#3b4450]">Queue: 2</span>
            </div>
            <div className="mt-5 space-y-4">
              {[
                { title: "Swap fried noodles → soup noodles", impact: "expected Δ −6 mg/dL" },
                { title: "Add water intake reminder @ 14:00", impact: "expected Δ +0.5L" },
              ].map((row) => (
                <div key={row.title} className="border border-dashed border-[#c9cfd7] p-4">
                  <div className="text-sm font-semibold">{row.title}</div>
                  <div className="mt-2 text-xs font-mono text-[#4a5562]">{row.impact}</div>
                </div>
              ))}
            </div>
            <Link href="/style-samples" className="mt-6 inline-block text-xs uppercase tracking-[0.2em] text-[#5a6570]">
              Back to samples →
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
