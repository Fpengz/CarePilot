"use client";

import Link from "next/link";

export default function EditorialSamplePage() {
  return (
    <div
      className="min-h-screen px-6 py-10"
      style={{
        background:
          "linear-gradient(180deg, #f5f0e8 0%, #efe7da 55%, #f8f4ee 100%)",
        color: "#2f2a22",
        fontFamily: "\"Fraunces\", \"Iowan Old Style\", serif",
      }}
    >
      <div className="mx-auto max-w-6xl space-y-12">
        <header className="grid gap-8 lg:grid-cols-[1.4fr_0.9fr] lg:items-end">
          <div className="space-y-4">
            <p className="text-xs uppercase tracking-[0.3em] text-[#6b5f4f]">CarePilot — Editorial</p>
            <h1 className="text-5xl leading-[1.05]">
              A clinical companion that reads like a magazine, not a dashboard.
            </h1>
            <p className="text-lg text-[#4a4035] leading-relaxed max-w-xl">
              Long-form insight blocks, confident typographic hierarchy, and a calm
              palette that respects both patients and clinicians.
            </p>
          </div>
          <div className="rounded-[24px] border border-[#d8ccbc] bg-[#fbf7f1] p-6 shadow-[0_24px_60px_rgba(75,60,40,0.12)]">
            <div className="text-xs uppercase tracking-[0.28em] text-[#7a6a55]">Today</div>
            <div className="mt-3 text-3xl">2 gentle nudges</div>
            <p className="mt-3 text-sm text-[#6a5c4b]">
              A new meal pattern suggests a slow‑release carb adjustment before dinner.
            </p>
            <div className="mt-6 flex items-center gap-3">
              <button className="rounded-full bg-[#2f2a22] px-5 py-2 text-xs uppercase tracking-[0.2em] text-[#fdfbf7]">
                Review
              </button>
              <button className="rounded-full border border-[#cbbba8] px-5 py-2 text-xs uppercase tracking-[0.2em] text-[#4a4035]">
                Save
              </button>
            </div>
          </div>
        </header>

        <section className="grid gap-8 lg:grid-cols-[0.8fr_1fr]">
          <div className="space-y-6">
            <div className="text-xs uppercase tracking-[0.28em] text-[#7a6a55]">Case snapshot</div>
            <div className="space-y-4 text-[#3e342a] text-base leading-relaxed">
              <p>
                The last seven days show a consistent post‑lunch glucose spike, paired with
                high sodium intake. The pattern is narrow enough to intervene without
                disrupting breakfast or dinner routines.
              </p>
              <p>
                The companion suggests one adjustment per day—small enough to keep compliance
                high, while still driving measurable impact.
              </p>
            </div>
            <blockquote className="border-l-2 border-[#cbbba8] pl-4 text-lg italic text-[#5a4b3c]">
              “We should aim for 10–12 grams less sodium at lunch, not a full menu rewrite.”
            </blockquote>
          </div>
          <div className="grid gap-5 sm:grid-cols-2">
            {[
              { label: "Morning trend", value: "Stable", desc: "Fasting glucose within range." },
              { label: "Lunch delta", value: "+18%", desc: "Spike traced to hawker fried items." },
              { label: "Hydration", value: "Low", desc: "Fluid intake below target." },
              { label: "Adherence", value: "84%", desc: "Medication timing reliable." },
            ].map((card) => (
              <div
                key={card.label}
                className="rounded-[20px] border border-[#d8ccbc] bg-[#fffaf2] p-5 shadow-[0_18px_45px_rgba(70,55,40,0.08)]"
                style={{ fontFamily: "\"Source Sans 3\", sans-serif" }}
              >
                <div className="text-xs uppercase tracking-[0.26em] text-[#8a7a65]">{card.label}</div>
                <div className="mt-2 text-2xl text-[#2f2a22]">{card.value}</div>
                <p className="mt-3 text-sm text-[#6a5c4b]">{card.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1fr_0.6fr]">
          <div className="rounded-[28px] border border-[#d8ccbc] bg-[#fffdf8] p-7 shadow-[0_24px_60px_rgba(70,55,40,0.1)]">
            <div className="text-xs uppercase tracking-[0.28em] text-[#8a7a65]">Clinician digest</div>
            <h2 className="mt-3 text-3xl">Lunch spike pattern, stable overnight markers</h2>
            <p className="mt-4 text-base text-[#4a4035] leading-relaxed">
              No acute alerts. Recommend a low‑sodium swap and a hydration nudge. Patient
              compliance is high; we can tighten lunch guidance without increasing burden.
            </p>
            <div className="mt-6 grid gap-3 text-sm text-[#5a4b3c]">
              <div>Recommended intervention: Swap fried noodles → soup noodles.</div>
              <div>Estimated impact: −6 mg/dL average post‑lunch glucose.</div>
            </div>
          </div>
          <div className="space-y-4">
            <div className="rounded-[20px] border border-[#d8ccbc] bg-[#fdf6ec] p-5">
              <div className="text-xs uppercase tracking-[0.24em] text-[#8a7a65]">Signal</div>
              <p className="mt-2 text-base text-[#4a4035]">Patient mood: calm, receptive.</p>
            </div>
            <div className="rounded-[20px] border border-[#d8ccbc] bg-[#fdf6ec] p-5">
              <div className="text-xs uppercase tracking-[0.24em] text-[#8a7a65]">Next touchpoint</div>
              <p className="mt-2 text-base text-[#4a4035]">Wednesday lunch check‑in.</p>
            </div>
            <Link href="/style-samples" className="text-xs uppercase tracking-[0.2em] text-[#6b5f4f]">
              Back to samples →
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
