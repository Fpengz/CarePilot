import type { LucideIcon } from "lucide-react";
import {
  Bell,
  ChartColumn,
  House,
  LogIn,
  UserPlus,
  Salad,
  ShieldAlert,
  Workflow,
} from "lucide-react";

export type NavGroup = "main" | "admin" | "auth";

export interface RouteMeta {
  href: string;
  label: string;
  pageTitle: string;
  breadcrumbLabel: string;
  group: NavGroup;
  icon: LucideIcon;
  showInSidebar: boolean;
  mobileTab: boolean;
  requiredAnyScopes?: string[];
}

export const ROUTE_META: RouteMeta[] = [
  {
    href: "/login",
    label: "Login",
    pageTitle: "Sign In",
    breadcrumbLabel: "Login",
    group: "auth",
    icon: LogIn,
    showInSidebar: false,
    mobileTab: false,
  },
  {
    href: "/signup",
    label: "Sign Up",
    pageTitle: "Sign Up",
    breadcrumbLabel: "Sign Up",
    group: "auth",
    icon: UserPlus,
    showInSidebar: false,
    mobileTab: false,
  },
  {
    href: "/dashboard",
    label: "Dashboard",
    pageTitle: "Dashboard",
    breadcrumbLabel: "Dashboard",
    group: "main",
    icon: House,
    showInSidebar: true,
    mobileTab: true,
  },
  {
    href: "/meals",
    label: "Meals",
    pageTitle: "Meals",
    breadcrumbLabel: "Meals",
    group: "main",
    icon: Salad,
    showInSidebar: true,
    mobileTab: true,
  },
  {
    href: "/reports",
    label: "Reports",
    pageTitle: "Reports",
    breadcrumbLabel: "Reports",
    group: "main",
    icon: ChartColumn,
    showInSidebar: true,
    mobileTab: true,
  },
  {
    href: "/reminders",
    label: "Reminders",
    pageTitle: "Reminders",
    breadcrumbLabel: "Reminders",
    group: "main",
    icon: Bell,
    showInSidebar: true,
    mobileTab: true,
  },
  {
    href: "/alerts",
    label: "Alerts",
    pageTitle: "Alerts",
    breadcrumbLabel: "Alerts",
    group: "admin",
    icon: ShieldAlert,
    showInSidebar: true,
    mobileTab: false,
    requiredAnyScopes: ["alert:trigger", "alert:timeline:read"],
  },
  {
    href: "/workflows",
    label: "Workflows",
    pageTitle: "Workflows",
    breadcrumbLabel: "Workflows",
    group: "admin",
    icon: Workflow,
    showInSidebar: true,
    mobileTab: false,
    requiredAnyScopes: ["workflow:read", "workflow:replay"],
  },
];

export const CORE_MOBILE_TABS = ROUTE_META.filter((route) => route.mobileTab);

export function findRouteMeta(pathname: string): RouteMeta | undefined {
  return ROUTE_META.find((route) => route.href === pathname);
}

export function isAdminRoute(route: RouteMeta): boolean {
  return route.group === "admin";
}

export function routeIsEnabled(route: RouteMeta, hasScope: (scope: string) => boolean): boolean {
  if (!route.requiredAnyScopes || route.requiredAnyScopes.length === 0) return true;
  return route.requiredAnyScopes.some((scope) => hasScope(scope));
}
