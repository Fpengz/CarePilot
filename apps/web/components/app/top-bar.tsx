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
    <header className="app-panel sticky top-2 z-20 mb-6 border border-[color:var(--border)] bg-[color:var(--panel)] p-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--muted-foreground)]">
            <span>Dietary Guardian</span>
            <ChevronRight className="h-3 w-3" aria-hidden />
            <span>{breadcrumb}</span>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="truncate text-2xl font-semibold leading-tight md:text-[2.2rem]">
              {pageTitle}
            </h2>
            {route?.group === "admin" ? <Badge variant="outline">Admin Area</Badge> : null}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:justify-end">
          <div className="app-toolbar-chip hidden items-center gap-1.5 sm:flex">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-disabled="true"
              title="Search coming soon"
              className="h-9 gap-2 px-3"
            >
              <Search className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">Search</span>
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-disabled="true"
              title="Notifications coming soon"
              className="h-9 px-2.5"
            >
              <Bell className="h-4 w-4" aria-hidden />
              <span className="sr-only">Notifications (coming soon)</span>
            </Button>
          </div>
          <div className="app-toolbar-chip">
            <ThemeToggle />
          </div>
          {status === "loading" ? (
            <Badge variant="outline">Session loading</Badge>
          ) : status === "unauthenticated" || !user ? (
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="hidden sm:inline-flex">Not signed in</Badge>
              <Button asChild size="sm">
                <Link href="/login">Sign in</Link>
              </Button>
            </div>
          ) : (
            <AccountPanel />
          )}
        </div>
      </div>
    </header>
  );
}
