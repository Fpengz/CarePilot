"use client";

import Link from "next/link";

export default function SoftPastelSamplePage() {
  return (
    <div
      className="min-h-screen px-6 py-10"
      style={{
        background:
          "radial-gradient(60rem 40rem at 10% -20%, #f9d8e8 0%, transparent 60%), radial-gradient(50rem 40rem at 100% 0%, #d4e5ff 0%, transparent 65%), linear-gradient(180deg, #faf7ff 0%, #f3f7ff 100%)",
        color: "#2b2e3a",
        fontFamily: "\"Manrope\", \"Source Sans 3\", sans-serif",
      }}
    >
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;500;700&display=swap');
      `}</style>
      <div className="mx-auto max-w-6xl space-y-12">
        <header className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-4">
            <p className="text-xs uppercase tracking-[0.3em] text-[#6b6f85]">Soft pastel system</p>
            <h1 className="text-5xl leading-[1.05] font-semibold">
              Calm, minimal, and quietly supportive.
            </h1>
            <p className="text-base text-[#5a6174] max-w-xl">
              Gentle gradients, muted contrast, and a generous layout for low‑stress guidance.
            </p>
          </div>
          <div className="rounded-[28px] bg-white/70 p-6 shadow-[0_24px_70px_rgba(150,160,200,0.2)] backdrop-blur">
            <div className="text-xs uppercase tracking-[0.28em] text-[#7a8098]">Focus</div>
            <div className="mt-3 text-3xl">Lunch balance</div>
            <p className="mt-3 text-sm text-[#6d7488]">
              One gentle swap and a hydration nudge keep things stable.
            </p>
            <div className="mt-6 flex gap-3">
              <button className="rounded-full bg-[#6b7cff] px-5 py-2 text-xs uppercase tracking-[0.2em] text-white shadow-[0_12px_30px_rgba(107,124,255,0.35)]">
                Accept
              </button>
              <button className="rounded-full border border-[#d1d6ee] px-5 py-2 text-xs uppercase tracking-[0.2em] text-[#5a6174]">
                Later
              </button>
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-4">
            <div className="rounded-[24px] bg-white/75 p-5 shadow-[0_16px_50px_rgba(170,180,210,0.18)]">
              <div className="text-xs uppercase tracking-[0.28em] text-[#7a8098]">Case note</div>
              <p className="mt-3 text-sm text-[#5a6174]">
                Post‑lunch spike detected. Medication adherence stable. Recommend a single swap.
              </p>
            </div>
            <div className="rounded-[24px] bg-white/75 p-5 shadow-[0_16px_50px_rgba(170,180,210,0.18)]">
              <div className="text-xs uppercase tracking-[0.28em] text-[#7a8098]">Signals</div>
              <ul className="mt-3 space-y-2 text-sm text-[#5a6174]">
                <li>Glucose +18%</li>
                <li>Sodium 900mg</li>
                <li>Hydration ‑350ml</li>
              </ul>
            </div>
          </div>
          <div className="rounded-[26px] bg-white/80 p-6 shadow-[0_24px_70px_rgba(150,160,200,0.2)]">
            <div className="text-xs uppercase tracking-[0.28em] text-[#7a8098]">Interventions</div>
            <div className="mt-5 space-y-4">
              {[
                "Swap fried noodles → soup noodles",
                "Hydration reminder @ 14:00",
                "Evening check‑in prompt",
              ].map((item) => (
                <div key={item} className="rounded-[18px] bg-[#f4f6ff] px-4 py-3 text-sm text-[#4f566a]">
                  {item}
                </div>
              ))}
            </div>
            <Link href="/style-samples" className="mt-6 inline-block text-xs uppercase tracking-[0.2em] text-[#7a8098]">
              Back to samples →
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
