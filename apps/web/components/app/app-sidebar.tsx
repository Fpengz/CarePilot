"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { getSidebarSections } from "@/components/app/route-meta";
import { SidebarNav } from "@/components/app/sidebar-nav";
import { Badge } from "@/components/ui/badge";
import { useSidebar } from "@/components/app/sidebar-provider";
import { Button } from "@/components/ui/button";
import { CompanionIcon } from "@/components/icons/companion-icon";
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
                <CompanionIcon className="h-6 w-6" />
              </div>
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <div className="rounded-lg bg-[color:var(--accent)] p-1.5 text-white shadow-sm">
                    <CompanionIcon className="h-4 w-4" />
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
