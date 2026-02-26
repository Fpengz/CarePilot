"use client";

import { AppSidebar } from "@/components/app/app-sidebar";
import { MobileNav } from "@/components/app/mobile-nav";
import { TopBar } from "@/components/app/top-bar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-shell">
      <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)] lg:gap-5">
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
