"use client";

import Link from "next/link";
import { Menu, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname } from "next/navigation";

import { CORE_MOBILE_TABS, ROUTE_META } from "@/components/app/route-meta";
import { SidebarNav } from "@/components/app/sidebar-nav";
import { useSession } from "@/components/app/session-provider";
import { useDialogA11y } from "@/components/app/use-dialog-a11y";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const mainRoutes = ROUTE_META.filter((route) => route.group === "main" && route.showInSidebar);
const adminRoutes = ROUTE_META.filter((route) => route.group === "admin" && route.showInSidebar);

export function MobileNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { status, user } = useSession();
  const openButtonRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useDialogA11y({
    open,
    containerRef: drawerRef,
    initialFocusRef: closeButtonRef,
    returnFocusRef: openButtonRef,
    onClose: () => setOpen(false),
  });

  const moreActive = useMemo(
    () => !CORE_MOBILE_TABS.some((route) => route.href === pathname),
    [pathname],
  );

  return (
    <>
      <div className="lg:hidden">
        <div className="pointer-events-none fixed inset-x-0 bottom-3 z-30 px-3">
          <div className="pointer-events-auto app-panel mx-auto max-w-xl p-2">
            <nav aria-label="Mobile primary navigation" className="grid grid-cols-5 gap-1">
              {CORE_MOBILE_TABS.map((route) => {
                const Icon = route.icon;
                const active = pathname === route.href;
                return (
                  <Link
                    key={route.href}
                    href={route.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex min-h-[52px] flex-col items-center justify-center rounded-lg px-1 py-2 text-[11px] font-medium",
                      active
                        ? "bg-[color:var(--accent)]/14 text-[color:var(--accent)] dark:bg-[color:var(--accent)]/18 dark:text-[#b9efe4]"
                        : "text-[color:var(--muted-foreground)] hover:bg-black/5 dark:hover:bg-white/5",
                    )}
                  >
                    <Icon className="mb-1 h-4 w-4" aria-hidden />
                    <span className="truncate">{route.label}</span>
                  </Link>
                );
              })}
              <button
                ref={openButtonRef}
                type="button"
                aria-label="Open navigation drawer"
                aria-expanded={open}
                aria-controls="mobile-nav-drawer"
                onClick={() => setOpen(true)}
                className={cn(
                  "flex min-h-[52px] flex-col items-center justify-center rounded-lg px-1 py-2 text-[11px] font-medium",
                  moreActive
                    ? "bg-[color:var(--accent)]/14 text-[color:var(--accent)] dark:bg-[color:var(--accent)]/18 dark:text-[#b9efe4]"
                    : "text-[color:var(--muted-foreground)] hover:bg-black/5 dark:hover:bg-white/5",
                )}
              >
                <Menu className="mb-1 h-4 w-4" aria-hidden />
                <span>More</span>
              </button>
            </nav>
          </div>
        </div>
      </div>

      {open ? (
        <div className="lg:hidden">
          <div className="fixed inset-0 z-40 bg-black/50" onClick={() => setOpen(false)} aria-hidden />
          <div
            id="mobile-nav-drawer"
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
            className="fixed inset-y-0 right-0 z-50 w-[min(92vw,24rem)] border-l border-[color:var(--border)] bg-[color:var(--background)] p-4 shadow-2xl"
          >
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold">Navigation</div>
                <div className="text-xs text-[color:var(--muted-foreground)]">Core routes + admin area</div>
              </div>
              <Button
                ref={closeButtonRef}
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setOpen(false)}
                className="px-2.5"
              >
                <X className="h-4 w-4" aria-hidden />
                <span className="sr-only">Close navigation</span>
              </Button>
            </div>

            <div className="mb-4 flex flex-wrap gap-2">
              {status === "authenticated" && user ? (
                <>
                  <Badge>{user.account_role}</Badge>
                  <Badge variant="outline">{user.profile_mode}</Badge>
                </>
              ) : (
                <Badge variant="outline">{status === "loading" ? "Session loading" : "Not signed in"}</Badge>
              )}
            </div>

            <div className="space-y-4">
              <SidebarNav routes={mainRoutes} activePathname={pathname} title="Primary" titleId="mobile-sidebar-primary" />
              <SidebarNav routes={adminRoutes} activePathname={pathname} title="Admin" titleId="mobile-sidebar-admin" />
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
