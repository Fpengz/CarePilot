"use client";

import Link from "next/link";

export default function RetroFuturistSamplePage() {
  return (
    <div
      className="min-h-screen px-6 py-10"
      style={{
        background:
          "radial-gradient(60rem 40rem at 10% -20%, rgba(255, 200, 100, 0.45) 0%, transparent 60%), radial-gradient(50rem 40rem at 100% 0%, rgba(80, 210, 200, 0.35) 0%, transparent 65%), linear-gradient(180deg, #0f1418 0%, #0c1115 100%)",
        color: "#f4f0e8",
        fontFamily: "\"Space Grotesk\", \"Source Sans 3\", sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
      `}</style>
      <div className="mx-auto max-w-6xl space-y-12">
        <header className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-4">
            <p className="text-xs uppercase tracking-[0.32em] text-[#c1f7e7]">Retro‑futurist stack</p>
            <h1 className="text-5xl leading-[1.05] font-semibold">
              An optimistic clinical cockpit with glow and geometry.
            </h1>
            <p className="text-base text-[#d7d0c6] max-w-xl">
              Energy and momentum without losing legibility: strong contrast, luminous accents,
              and clear command surfaces.
            </p>
          </div>
          <div className="rounded-[26px] border border-white/15 bg-white/5 p-6 shadow-[0_24px_70px_rgba(0,0,0,0.4)] backdrop-blur">
            <div className="text-xs uppercase tracking-[0.28em] text-[#f1d59e]">Pulse</div>
            <div className="mt-3 text-3xl">Guidance ready</div>
            <p className="mt-3 text-sm text-[#d7d0c6]">
              Two adjustments queued. Risk profile stable, ready for gentle tuning.
            </p>
            <div className="mt-6 flex gap-3">
              <button className="rounded-full bg-[#f2b66d] px-5 py-2 text-xs uppercase tracking-[0.2em] text-[#1a1410] shadow-[0_12px_30px_rgba(242,182,109,0.35)]">
                Engage
              </button>
              <button className="rounded-full border border-[#54e0d0] px-5 py-2 text-xs uppercase tracking-[0.2em] text-[#54e0d0]">
                Delay
              </button>
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-4">
            <div className="rounded-[24px] border border-white/15 bg-white/5 p-5">
              <div className="text-xs uppercase tracking-[0.28em] text-[#f1d59e]">Signal map</div>
              <p className="mt-3 text-sm text-[#d7d0c6] leading-relaxed">
                Post‑lunch spike detected. Hydration deficit 350ml. Stress index steady.
              </p>
            </div>
            <div className="rounded-[24px] border border-white/15 bg-white/5 p-5">
              <div className="text-xs uppercase tracking-[0.28em] text-[#f1d59e]">Mood</div>
              <p className="mt-3 text-sm text-[#d7d0c6]">Receptive, low fatigue.</p>
            </div>
          </div>
          <div className="rounded-[28px] border border-white/15 bg-gradient-to-br from-white/10 to-white/5 p-6 shadow-[0_26px_70px_rgba(0,0,0,0.4)]">
            <div className="text-xs uppercase tracking-[0.28em] text-[#c1f7e7]">Action deck</div>
            <div className="mt-5 space-y-4">
              {[
                { title: "Swap fried noodles → soup noodles", note: "Expected Δ −6 mg/dL" },
                { title: "Hydration nudge at 14:00", note: "Expected Δ +0.5L" },
                { title: "Evening check‑in prompt", note: "Reinforce adherence" },
              ].map((card) => (
                <div
                  key={card.title}
                  className="rounded-[20px] border border-white/15 bg-black/35 p-4"
                >
                  <div className="text-sm font-semibold">{card.title}</div>
                  <div className="mt-2 text-xs text-[#d7d0c6]">{card.note}</div>
                </div>
              ))}
            </div>
            <Link href="/style-samples" className="mt-6 inline-block text-xs uppercase tracking-[0.2em] text-[#c1f7e7]">
              Back to samples →
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
