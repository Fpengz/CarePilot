"use client";

import Link from "next/link";
import { Lock } from "lucide-react";

import { routeIsEnabled, type RouteMeta } from "@/components/app/route-meta";
import { useSession } from "@/components/app/session-provider";
import { cn } from "@/lib/utils";

function NavItem({ route, active }: { route: RouteMeta; active: boolean }) {
  const { hasScope, status } = useSession();
  const enabled = routeIsEnabled(route, hasScope);
  const isDisabled = route.requiredAnyScopes && route.requiredAnyScopes.length > 0 && (!enabled || status === "loading");
  const Icon = route.icon;

  const baseClass =
    "flex w-full items-center justify-between rounded-xl border px-3 py-2.5 text-sm font-medium transition";
  const enabledClass = cn(
    "border-[color:var(--border)] bg-white/70 text-[color:var(--foreground)] hover:-translate-y-px hover:bg-white dark:bg-[color:var(--panel-soft)] dark:text-[#ece6d8] dark:hover:bg-[color:var(--card)]",
    active &&
      "border-[color:var(--accent)]/40 bg-[color:var(--accent)]/12 text-[color:var(--accent)] dark:border-[color:var(--accent)]/35 dark:bg-[color:var(--accent)]/18 dark:text-[#b9efe4]",
  );
  const disabledClass =
    "cursor-not-allowed border-[color:var(--border)] bg-white/45 text-[color:var(--muted-foreground)] opacity-90 dark:bg-[color:var(--panel-soft)]/60 dark:text-[#aca89f]";

  if (isDisabled) {
    return (
      <div
        aria-disabled="true"
        title="Admin access required"
        className={cn(baseClass, disabledClass)}
      >
        <span className="flex items-center gap-2">
          <Icon className="h-4 w-4" aria-hidden />
          {route.label}
        </span>
        <Lock className="h-4 w-4" aria-hidden />
      </div>
    );
  }

  return (
    <Link
      href={route.href}
      aria-current={active ? "page" : undefined}
      className={cn(baseClass, enabledClass)}
    >
      <span className="flex items-center gap-2">
        <Icon className="h-4 w-4" aria-hidden />
        {route.label}
      </span>
    </Link>
  );
}

export function SidebarNav({
  routes,
  activePathname,
  title,
  titleId,
}: {
  routes: RouteMeta[];
  activePathname: string;
  title: string;
  titleId: string;
}) {
  const groupActive = routes.some((route) => route.href === activePathname);

  return (
    <section aria-labelledby={titleId} className="space-y-2">
      <div
        id={titleId}
        className={cn(
          "flex items-center justify-between rounded-lg px-2 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-[color:var(--muted-foreground)]",
          groupActive &&
            "bg-[color:var(--accent)]/8 text-[color:var(--accent)] dark:bg-[color:var(--accent)]/12 dark:text-[#b9efe4]",
        )}
      >
        {title}
        {groupActive ? (
          <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--accent)] dark:bg-[#b9efe4]" aria-hidden />
        ) : null}
      </div>
      <div className="space-y-1.5">
        {routes.map((route) => (
          <NavItem key={route.href} route={route} active={activePathname === route.href} />
        ))}
      </div>
    </section>
  );
}
