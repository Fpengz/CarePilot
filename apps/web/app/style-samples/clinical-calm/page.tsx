"use client";

import Link from "next/link";

const metrics = [
  { label: "Calories", value: "1,420", unit: "kcal", delta: "+6% vs target" },
  { label: "Sodium", value: "1,980", unit: "mg", delta: "Near upper band" },
  { label: "Protein", value: "72", unit: "g", delta: "On track" },
];

const meals = [
  { title: "Breakfast", desc: "Oats, soy milk, kiwi", score: "Balanced" },
  { title: "Lunch", desc: "Chicken rice, clear soup", score: "High sodium" },
  { title: "Dinner", desc: "Steamed fish, brown rice", score: "Ideal" },
];

const timeline = [
  { time: "07:40", label: "Oats + kiwi", note: "Low GI, stable energy" },
  { time: "12:15", label: "Chicken rice", note: "Ask for less sauce" },
  { time: "18:30", label: "Steamed fish set", note: "Great protein density" },
];

const reminders = [
  { title: "Water check-in", time: "15:00", status: "Due" },
  { title: "Medication", time: "21:00", status: "Scheduled" },
];

const activity = [
  { label: "Blood glucose logged", meta: "2 hours ago" },
  { label: "Meal photo analyzed", meta: "Today, 12:18" },
  { label: "Weekly report shared", meta: "Yesterday" },
];

export default function ClinicalCalmSamplePage() {
  return (
    <div className="min-h-screen bg-[color:var(--background)] text-[color:var(--foreground)]">
      <div className="app-shell space-y-16">
        <header className="grid gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div className="space-y-6">
            <p className="section-kicker">CarePilot</p>
            <h1 className="text-4xl font-semibold leading-[1.05] tracking-[-0.02em] md:text-5xl">
              Clinical clarity for everyday nutrition decisions.
            </h1>
            <p className="text-lg text-[color:var(--muted-foreground)] leading-relaxed">
              A trusted companion that reads each meal, checks health context, and
              delivers a single confident next step.
            </p>
            <div className="flex flex-wrap items-center gap-4">
              <button className="rounded-full bg-[color:var(--accent)] px-6 py-3 text-sm font-semibold text-[color:var(--accent-foreground)] shadow-[0_16px_32px_rgba(45,110,170,0.2)] transition hover:translate-y-[-1px]">
                Start today&apos;s plan
              </button>
              <p className="text-xs text-[color:var(--muted-foreground)]">
                Clinician-reviewed guidance from 12,000 SG food entries.
              </p>
            </div>
          </div>
          <div className="app-panel p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted-foreground)]">
                  Today snapshot
                </p>
                <p className="mt-2 text-2xl font-semibold">Nutrition score 84</p>
                <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">
                  Stable glucose. Sodium slightly elevated at lunch.
                </p>
              </div>
              <div className="h-16 w-16 rounded-full border border-[color:var(--border-soft)] bg-[color:var(--surface)] p-2">
                <div className="h-full w-full rounded-full border border-[color:var(--accent)] bg-[color:var(--panel-soft)]" />
              </div>
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              {metrics.map((item) => (
                <div key={item.label} className="metric-card">
                  <div className="text-xs uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
                    {item.label}
                  </div>
                  <div className="mt-2 text-2xl font-semibold">
                    {item.value}
                    <span className="ml-1 text-sm font-medium text-[color:var(--muted-foreground)]">
                      {item.unit}
                    </span>
                  </div>
                  <p className="mt-2 text-xs text-[color:var(--muted-foreground)]">{item.delta}</p>
                </div>
              ))}
            </div>
          </div>
        </header>

        <section className="space-y-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="section-kicker">Dashboard</p>
              <h2 className="text-2xl font-semibold">Today at a glance</h2>
            </div>
            <Link href="/style-samples" className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted-foreground)]">
              Back to samples →
            </Link>
          </div>

          <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="clinical-panel space-y-6">
              <div>
                <p className="section-kicker">Daily nutrition score</p>
                <div className="mt-3 flex items-end gap-4">
                  <p className="text-5xl font-semibold">84</p>
                  <div className="pb-2 text-sm text-[color:var(--muted-foreground)]">
                    +4 since last week
                  </div>
                </div>
                <div className="mt-4 h-2 w-full rounded-full bg-[color:var(--border-soft)]">
                  <div className="h-2 w-[68%] rounded-full bg-[color:var(--accent)]" />
                </div>
              </div>
              <div className="clinical-divider" />
              <div>
                <p className="section-kicker">AI health insight</p>
                <p className="mt-3 text-base font-semibold">
                  Lunch sodium spike drives evening thirst and late snacking.
                </p>
                <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">
                  Recommend a lower-sodium lunch base and an afternoon hydration check-in.
                </p>
              </div>
            </div>

            <div className="grid gap-4">
              <div className="metric-card">
                <p className="section-kicker">Key metrics</p>
                <div className="mt-4 grid gap-3">
                  <div className="flex items-center justify-between text-sm">
                    <span>Carbs</span>
                    <span className="font-semibold">210 g</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span>Fiber</span>
                    <span className="font-semibold">23 g</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span>Hydration</span>
                    <span className="font-semibold">1.2 L</span>
                  </div>
                </div>
              </div>
              <div className="metric-card">
                <p className="section-kicker">Alert status</p>
                <p className="mt-3 text-base font-semibold">No urgent risks</p>
                <p className="mt-2 text-sm text-[color:var(--muted-foreground)]">
                  Maintain steady glucose and reduce lunch sodium to improve evening recovery.
                </p>
              </div>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="app-panel p-6 space-y-4">
              <p className="section-kicker">Meal summaries</p>
              <div className="grid gap-4">
                {meals.map((meal) => (
                  <div key={meal.title} className="flex items-center justify-between rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] px-4 py-3">
                    <div>
                      <p className="text-sm font-semibold">{meal.title}</p>
                      <p className="text-xs text-[color:var(--muted-foreground)]">{meal.desc}</p>
                    </div>
                    <span className="text-xs font-semibold text-[color:var(--accent)]">{meal.score}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-4">
              <div className="metric-card">
                <p className="section-kicker">Hydration</p>
                <div className="mt-3 flex items-end justify-between">
                  <p className="text-3xl font-semibold">1.2 L</p>
                  <p className="text-xs text-[color:var(--muted-foreground)]">Target 2.0 L</p>
                </div>
                <div className="mt-4 h-2 rounded-full bg-[color:var(--border-soft)]">
                  <div className="h-2 w-[60%] rounded-full bg-[color:var(--accent)]" />
                </div>
              </div>
              <div className="metric-card">
                <p className="section-kicker">Nutrition breakdown</p>
                <div className="mt-4 grid gap-3 text-xs text-[color:var(--muted-foreground)]">
                  <div className="flex items-center justify-between">
                    <span>Carbs</span>
                    <span>45%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Protein</span>
                    <span>30%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Fat</span>
                    <span>25%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="app-panel p-6 space-y-4">
              <p className="section-kicker">Meal timeline</p>
              <div className="space-y-3">
                {timeline.map((item) => (
                  <div key={item.time} className="flex items-start gap-3">
                    <div className="text-xs font-semibold text-[color:var(--muted-foreground)]">{item.time}</div>
                    <div>
                      <p className="text-sm font-semibold">{item.label}</p>
                      <p className="text-xs text-[color:var(--muted-foreground)]">{item.note}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="app-panel p-6 space-y-4">
              <p className="section-kicker">Reminders</p>
              <div className="space-y-3">
                {reminders.map((item) => (
                  <div key={item.title} className="flex items-center justify-between rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] px-4 py-3 text-sm">
                    <div>
                      <p className="font-semibold">{item.title}</p>
                      <p className="text-xs text-[color:var(--muted-foreground)]">{item.time}</p>
                    </div>
                    <span className="text-xs font-semibold text-[color:var(--accent)]">{item.status}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="app-panel p-6 space-y-4">
              <p className="section-kicker">Recent activity</p>
              <div className="space-y-3 text-sm">
                {activity.map((item) => (
                  <div key={item.label} className="rounded-xl border border-[color:var(--border-soft)] bg-[color:var(--surface)] px-4 py-3">
                    <p className="font-semibold">{item.label}</p>
                    <p className="text-xs text-[color:var(--muted-foreground)]">{item.meta}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
