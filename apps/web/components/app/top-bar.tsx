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
    <header className="app-panel sticky top-4 z-20 mb-4 p-3 md:p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-1 flex items-center gap-1 text-xs text-[color:var(--muted-foreground)]">
            <span>Dietary Guardian</span>
            <ChevronRight className="h-3 w-3" aria-hidden />
            <span>{breadcrumb}</span>
          </div>
          <h2 className="truncate text-xl font-semibold md:text-2xl">{pageTitle}</h2>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            aria-disabled="true"
            title="Search coming soon"
            className="gap-2"
          >
            <Search className="h-4 w-4" aria-hidden />
            <span className="hidden sm:inline">Search</span>
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            aria-disabled="true"
            title="Notifications coming soon"
            className="px-2.5"
          >
            <Bell className="h-4 w-4" aria-hidden />
            <span className="sr-only">Notifications (coming soon)</span>
          </Button>
          <ThemeToggle />
          {status === "loading" ? (
            <Badge variant="outline">Session loading</Badge>
          ) : status === "unauthenticated" || !user ? (
            <div className="flex items-center gap-2">
              <Badge variant="outline">Not signed in</Badge>
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
