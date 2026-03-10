"use client";

import { AppSidebar } from "@/components/app/app-sidebar";
import { MobileNav } from "@/components/app/mobile-nav";
import { TopBar } from "@/components/app/top-bar";
import { useSidebar } from "@/components/app/sidebar-provider";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { isCollapsed } = useSidebar();

  return (
    <div className="app-shell">
      <div
        className={cn(
          "grid gap-4 lg:gap-5 transition-all duration-300",
          isCollapsed ? "lg:grid-cols-[80px_minmax(0,1fr)]" : "lg:grid-cols-[280px_minmax(0,1fr)]"
        )}
      >
        <AppSidebar />
        <div className="min-w-0 pb-24 lg:pb-0">
          <TopBar />
          <main id="main-content">{children}</main>
        </div>
      </div>
      <MobileNav />
    </div>
  );
}
