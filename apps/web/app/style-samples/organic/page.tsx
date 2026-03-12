"use client";

import Link from "next/link";

export default function OrganicSamplePage() {
  return (
    <div
      className="min-h-screen px-6 py-10"
      style={{
        background:
          "radial-gradient(70rem 50rem at -5% -20%, #d7f2e2 0%, transparent 60%), radial-gradient(45rem 40rem at 100% -10%, #f7e3c9 0%, transparent 65%), linear-gradient(180deg, #fdf8f2 0%, #f3efe7 100%)",
        color: "#2f352f",
        fontFamily: "\"Source Sans 3\", \"Helvetica Neue\", sans-serif",
      }}
    >
      <div className="mx-auto max-w-6xl space-y-12">
        <header className="grid gap-10 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-4">
            <p className="text-xs uppercase tracking-[0.3em] text-[#6b7c64]">Soft organic system</p>
            <h1 className="text-5xl leading-[1.05] font-semibold" style={{ fontFamily: "\"Fraunces\", serif" }}>
              Gentle guidance with a warm, breathable rhythm.
            </h1>
            <p className="text-lg text-[#4f5d4c] max-w-xl">
              The companion feels like a calm wellness journal: rounded surfaces, airy spacing,
              and clear steps without clinical harshness.
            </p>
          </div>
          <div className="rounded-[28px] bg-white/70 p-6 shadow-[0_30px_70px_rgba(66,92,72,0.18)] backdrop-blur">
            <div className="text-xs uppercase tracking-[0.28em] text-[#7a8b75]">Today’s focus</div>
            <div className="mt-3 text-3xl text-[#263628]">Hydration + lunch balance</div>
            <p className="mt-3 text-sm text-[#5c6b58]">
              Swap one high‑salt lunch for a broth‑based bowl and add 500ml of water.
            </p>
            <div className="mt-6 flex gap-3">
              <button className="rounded-full bg-[#2f5e46] px-5 py-2 text-xs uppercase tracking-[0.2em] text-white shadow-[0_10px_30px_rgba(47,94,70,0.35)]">
                Accept
              </button>
              <button className="rounded-full border border-[#c9d4c6] px-5 py-2 text-xs uppercase tracking-[0.2em] text-[#4f5d4c]">
                Later
              </button>
            </div>
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1fr_1fr]">
          <div className="rounded-[30px] bg-white/80 p-6 shadow-[0_24px_60px_rgba(70,92,70,0.12)]">
            <div className="text-xs uppercase tracking-[0.28em] text-[#7a8b75]">Companion note</div>
            <p className="mt-4 text-lg text-[#3f4c3a] leading-relaxed">
              Your afternoons are steady. A small adjustment at lunch should ease the post‑meal
              spike without changing dinner patterns.
            </p>
            <div className="mt-6 grid gap-3 text-sm text-[#4f5d4c]">
              <div className="rounded-2xl bg-[#f0f4ed] px-4 py-3">Add one vegetable side.</div>
              <div className="rounded-2xl bg-[#f0f4ed] px-4 py-3">Choose soup‑based noodles.</div>
              <div className="rounded-2xl bg-[#f0f4ed] px-4 py-3">Finish with warm tea.</div>
            </div>
          </div>
          <div className="space-y-4">
            {[
              { title: "Stress signal", desc: "Mild fatigue noted; keep tasks short." },
              { title: "Meal rhythm", desc: "Lunch timing stable across 6 days." },
              { title: "Impact trend", desc: "Week‑over‑week glucose ↓ 4%." },
            ].map((item) => (
              <div key={item.title} className="rounded-[22px] border border-[#dde6d8] bg-white/70 p-5">
                <div className="text-xs uppercase tracking-[0.24em] text-[#7a8b75]">{item.title}</div>
                <p className="mt-2 text-sm text-[#4f5d4c]">{item.desc}</p>
              </div>
            ))}
            <Link href="/style-samples" className="text-xs uppercase tracking-[0.2em] text-[#6b7c64]">
              Back to samples →
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
