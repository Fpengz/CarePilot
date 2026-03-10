"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  ["Login", "/login"],
  ["Companion", "/companion"],
  ["Dashboard", "/dashboard"],
  ["Meals", "/meals"],
  ["Medications", "/medications"],
  ["Symptoms", "/symptoms"],
  ["Clinician Digest", "/clinician-digest"],
  ["Impact", "/impact"],
  ["Clinical Cards", "/clinical-cards"],
  ["Metrics", "/metrics"],
  ["Suggestions", "/suggestions"],
  ["Reminders", "/reminders"],
  ["Alerts", "/alerts"],
  ["Workflows", "/workflows"],
] as const;

export function HeaderNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="flex flex-wrap gap-2">
      {NAV_ITEMS.map(([label, href]) => {
        const isActive = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "rounded-xl border border-[color:var(--border)] bg-white/75 px-3 py-2 text-sm font-medium text-[color:var(--foreground)] transition hover:-translate-y-px hover:bg-white dark:bg-[color:var(--panel-soft)] dark:text-[#ece6d8] dark:hover:bg-[color:var(--card)]",
              isActive &&
                "border-[color:var(--accent)]/40 bg-[color:var(--accent)]/12 text-[color:var(--accent)] shadow-[inset_0_0_0_1px_rgba(0,0,0,0.02)] dark:border-[color:var(--accent)]/35 dark:bg-[color:var(--accent)]/18 dark:text-[#b9efe4]",
            )}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
