"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ROUTE_META } from "@/components/app/route-meta";
import { SidebarNav } from "@/components/app/sidebar-nav";
import { Badge } from "@/components/ui/badge";

const mainRoutes = ROUTE_META.filter((route) => route.group === "main" && route.showInSidebar);
const adminRoutes = ROUTE_META.filter((route) => route.group === "admin" && route.showInSidebar);

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:block">
      <div className="app-panel sticky top-6 p-4">
        <div className="mb-4 space-y-2">
          <Link href="/dashboard" className="block">
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold leading-tight">Dietary Guardian</h1>
              <Badge variant="outline">Foundation</Badge>
            </div>
            <p className="app-muted mt-1 text-sm leading-5">
              Wellness + care support with account-role and scope-aware access.
            </p>
          </Link>
        </div>

        <div className="space-y-4">
          <SidebarNav routes={mainRoutes} activePathname={pathname} title="Primary" titleId="sidebar-primary-nav" />
          <SidebarNav routes={adminRoutes} activePathname={pathname} title="Admin" titleId="sidebar-admin-nav" />
        </div>
      </div>
    </aside>
  );
}
