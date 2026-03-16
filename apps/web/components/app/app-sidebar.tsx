"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { getSidebarSections } from "@/components/app/route-meta";
import { SidebarNav } from "@/components/app/sidebar-nav";
import { Badge } from "@/components/ui/badge";
import { useSidebar } from "@/components/app/sidebar-provider";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function AppSidebar() {
  const pathname = usePathname();
  const { isCollapsed, toggleCollapsed } = useSidebar();
  const mainSections = getSidebarSections("main");
  const adminSections = getSidebarSections("admin");

  return (
    <aside className="hidden lg:block">
      <div
        className={cn(
          "sticky top-8 flex flex-col transition-all duration-300 border-r border-[color:var(--border-soft)] h-[calc(100vh-4rem)]",
          isCollapsed ? "px-2 w-20" : "px-6 w-full"
        )}
      >
        <div className={cn("mb-10", isCollapsed ? "flex justify-center" : "space-y-3")}>
          <Link href="/dashboard" className="group block">
            {isCollapsed ? (
              <div className="rounded-xl bg-[color:var(--accent)] p-2.5 text-white shadow-sm transition-transform group-hover:scale-105">
                <DashboardMark className="h-6 w-6" />
              </div>
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <div className="rounded-lg bg-[color:var(--accent)] p-1.5 text-white shadow-sm">
                    <DashboardMark className="h-4 w-4" />
                  </div>
                  <h1 className="text-lg font-bold leading-tight tracking-tight">
                    Guardian
                  </h1>
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant="outline" className="rounded-full px-2 py-0 text-[10px] font-bold uppercase tracking-wider opacity-60">
                    Foundation
                  </Badge>
                </div>
              </>
            )}
          </Link>
        </div>

        <div className="flex-1 space-y-8 overflow-y-auto pr-2 scrollbar-hide">
          {mainSections.map((section) => (
            <SidebarNav
              key={section.id}
              routes={section.routes}
              activePathname={pathname}
              title={section.title}
              titleId={`sidebar-${section.id}-nav`}
              isCollapsed={isCollapsed}
            />
          ))}
          {adminSections.map((section) => (
            <SidebarNav
              key={section.id}
              routes={section.routes}
              activePathname={pathname}
              title={section.title}
              titleId={`sidebar-${section.id}-nav`}
              isCollapsed={isCollapsed}
            />
          ))}
        </div>

        <div
          className={cn(
            "mt-6 flex border-t border-[color:var(--border-soft)] py-6",
            isCollapsed ? "justify-center" : "justify-between items-center"
          )}
        >
          {!isCollapsed && (
            <span className="text-[10px] font-bold uppercase tracking-widest text-[color:var(--muted-foreground)] opacity-50">
              v0.1.0
            </span>
          )}
          <Button
            variant="ghost"
            onClick={toggleCollapsed}
            className="h-8 w-8 p-0 rounded-lg text-[color:var(--muted-foreground)] hover:bg-[color:var(--muted)] hover:text-[color:var(--foreground)]"
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </aside>

  );
}

function DashboardMark({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 6.5h8a3 3 0 0 1 3 3v3a3 3 0 0 1-3 3H9.5l-3.5 2v-2H6a3 3 0 0 1-3-3v-3a3 3 0 0 1 3-3Z" />
      <path d="M12 11.5c-.6-1-2.1-1.3-3-.2-1 .9-.6 2.6.7 3.3.7.4 1.5.9 2.3 1.6.8-.7 1.6-1.2 2.3-1.6 1.3-.7 1.7-2.4.7-3.3-.9-1.1-2.4-.8-3 .2Z" />
      <path d="M18.5 4.5 20.5 6.5 22.5 4.5" />
      <path d="M20.5 6.5V12a4 4 0 0 1-4 4h-1.2" />
      <path d="M19.4 9.2c.8.6 1.7.9 2.6 1.1" />
    </svg>
  );
}
