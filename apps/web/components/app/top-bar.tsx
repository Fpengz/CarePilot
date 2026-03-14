"use client";

import Link from "next/link";
import { Bell, ChevronRight, Search } from "lucide-react";
import { usePathname } from "next/navigation";

import { AccountPanel } from "@/components/app/account-panel";
import { findRouteMeta } from "@/components/app/route-meta";
import { useSession } from "@/components/app/session-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";

export function TopBar() {
  const pathname = usePathname();
  const route = findRouteMeta(pathname);
  const pageTitle = route?.pageTitle ?? "Page";
  const breadcrumb = route?.breadcrumbLabel ?? "Page";
  const { status, user } = useSession();

  return (
    <header className="sticky top-0 z-20 mb-10 flex h-20 items-center border-b border-[color:var(--border-soft)] bg-[color:var(--background)]/80 backdrop-blur-md">
      <div className="flex w-full items-center justify-between">
        <div className="min-w-0">
          <div className="mb-1 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-[color:var(--muted-foreground)] opacity-70">
            <span>Dietary Guardian</span>
            <ChevronRight className="h-2.5 w-2.5 opacity-40" aria-hidden />
            <span>{breadcrumb}</span>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="truncate text-xl font-bold tracking-tight md:text-2xl">
              {pageTitle}
            </h2>
            {route?.group === "admin" ? <Badge variant="outline" className="text-[10px]">Admin Area</Badge> : null}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden items-center gap-1 sm:flex">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-disabled="true"
              title="Search coming soon"
              className="h-9 px-3 text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)]"
            >
              <Search className="h-4 w-4" aria-hidden />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-disabled="true"
              title="Notifications coming soon"
              className="h-9 px-3 text-[color:var(--muted-foreground)] hover:text-[color:var(--foreground)]"
            >
              <Bell className="h-4 w-4" aria-hidden />
            </Button>
          </div>
          <div className="h-4 w-px bg-[color:var(--border-soft)] hidden sm:block" />
          <ThemeToggle />
          <div className="h-4 w-px bg-[color:var(--border-soft)]" />
          {status === "loading" ? (
            <div className="h-8 w-8 animate-pulse rounded-full bg-[color:var(--muted)]" />
          ) : status === "unauthenticated" || !user ? (
            <Button asChild size="sm" className="rounded-full px-5">
              <Link href="/login">Sign in</Link>
            </Button>
          ) : (
            <AccountPanel />
          )}
        </div>
      </div>
    </header>

  );
}
