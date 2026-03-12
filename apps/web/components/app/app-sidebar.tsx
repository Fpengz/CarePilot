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
      <div
        className={cn(
          "app-panel sticky top-6 flex flex-col transition-all duration-300",
          isCollapsed ? "p-3 w-20" : "p-5 w-full"
        )}
      >
        <div className={cn("mb-6", isCollapsed ? "flex justify-center" : "space-y-2")}>
          <Link href="/dashboard" className="block">
            {isCollapsed ? (
              <div className="rounded-xl bg-[color:var(--accent)] p-2.5 text-white shadow-[0_10px_22px_rgba(16,92,182,0.18)]">
                <Salad className="h-6 w-6" />
              </div>
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-[1.35rem] font-semibold leading-[1.2] tracking-[-0.02em]">
                    Dietary Guardian
                  </h1>
                  <Badge variant="outline" className="self-start rounded-full px-3 py-1">
                    Foundation
                  </Badge>
                </div>
                <p className="app-muted mt-2 text-sm leading-5">
                  Clinical companion workspace.
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

        <div
          className={cn(
            "mt-4 flex border-t border-[color:var(--border)] pt-4",
            isCollapsed ? "justify-center" : "justify-end"
          )}
        >
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
