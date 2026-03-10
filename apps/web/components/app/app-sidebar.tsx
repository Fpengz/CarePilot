"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronLeft, ChevronRight, Salad } from "lucide-react";

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
      <div className={cn(
        "app-panel sticky top-6 flex flex-col transition-all duration-300",
        isCollapsed ? "p-3 w-20" : "p-4 xl:p-5 w-full"
      )}>
        <div className={cn("mb-5", isCollapsed ? "flex justify-center" : "space-y-2")}>
          <Link href="/dashboard" className="block">
            {isCollapsed ? (
              <div className="rounded-xl bg-[color:var(--accent)] p-2.5 text-white shadow-lg shadow-[color:var(--accent)]/20">
                <Salad className="h-6 w-6" />
              </div>
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-[1.75rem] font-semibold leading-[1.05] tracking-[-0.03em]">
                    Dietary
                    <br />
                    Guardian
                  </h1>
                  <Badge variant="outline" className="self-start">
                    Foundation
                  </Badge>
                </div>
                <p className="app-muted mt-1 text-sm leading-5">
                  Wellness + care support.
                </p>
              </>
            )}
          </Link>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto pr-1">
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

        <div className={cn("mt-4 pt-4 border-t border-[color:var(--border)] flex", isCollapsed ? "justify-center" : "justify-end")}>
          <Button
            variant="ghost"
            onClick={toggleCollapsed}
            className="h-8 w-8 p-0 rounded-lg text-[color:var(--muted-foreground)] hover:bg-[color:var(--accent)]/10 hover:text-[color:var(--accent)]"
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </aside>
  );
}
