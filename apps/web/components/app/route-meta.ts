import type { LucideIcon } from "lucide-react";
import {
  Activity,
  Bell,
  ChartColumn,
  FileHeart,
  FileText,
  House,
  HousePlus,
  LineChart,
  LogIn,
  Pill,
  UserPlus,
  Salad,
  Settings2,
  ShieldAlert,
  Workflow,
} from "lucide-react";

export type NavGroup = "main" | "admin" | "auth";
export type SidebarSectionId = "daily" | "care" | "insights" | "account" | "admin";

export interface RouteMeta {
  href: string;
  label: string;
  pageTitle: string;
  breadcrumbLabel: string;
  group: NavGroup;
  icon: LucideIcon;
  showInSidebar: boolean;
  mobileTab: boolean;
  sidebarSection?: SidebarSectionId;
  sidebarOrder?: number;
  requiredAnyScopes?: string[];
}

export interface SidebarSection {
  id: SidebarSectionId;
  title: string;
  group: Exclude<NavGroup, "auth">;
  routes: RouteMeta[];
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
    href: "/companion",
    label: "Companion",
    pageTitle: "Companion",
    breadcrumbLabel: "Companion",
    group: "main",
    icon: House,
    showInSidebar: true,
    mobileTab: true,
    sidebarSection: "daily",
    sidebarOrder: 1,
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
    sidebarSection: "daily",
    sidebarOrder: 2,
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
    sidebarSection: "daily",
    sidebarOrder: 3,
  },
  {
    href: "/suggestions",
    label: "Suggestions",
    pageTitle: "Suggestions",
    breadcrumbLabel: "Suggestions",
    group: "main",
    icon: ChartColumn,
    showInSidebar: false,
    mobileTab: false,
  },
  {
    href: "/reports",
    label: "Medical",
    pageTitle: "Medical Reports & Insights",
    breadcrumbLabel: "Medical",
    group: "main",
    icon: FileText,
    showInSidebar: true,
    mobileTab: false,
    sidebarSection: "care",
    sidebarOrder: 3,
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
    sidebarSection: "daily",
    sidebarOrder: 4,
  },
  {
    href: "/medications",
    label: "Medications",
    pageTitle: "Medications",
    breadcrumbLabel: "Medications",
    group: "main",
    icon: Pill,
    showInSidebar: true,
    mobileTab: false,
    sidebarSection: "care",
    sidebarOrder: 1,
  },
  {
    href: "/symptoms",
    label: "Symptoms",
    pageTitle: "Symptoms",
    breadcrumbLabel: "Symptoms",
    group: "main",
    icon: Activity,
    showInSidebar: true,
    mobileTab: false,
    sidebarSection: "care",
    sidebarOrder: 2,
  },
  {
    href: "/impact",
    label: "Impact",
    pageTitle: "Impact",
    breadcrumbLabel: "Impact",
    group: "main",
    icon: LineChart,
    showInSidebar: true,
    mobileTab: false,
    sidebarSection: "insights",
    sidebarOrder: 1,
  },
  {
    href: "/clinician-digest",
    label: "Clinician Digest",
    pageTitle: "Clinician Digest",
    breadcrumbLabel: "Clinician Digest",
    group: "main",
    icon: FileHeart,
    showInSidebar: true,
    mobileTab: false,
    sidebarSection: "insights",
    sidebarOrder: 2,
  },
  {
    href: "/household",
    label: "Household",
    pageTitle: "Household",
    breadcrumbLabel: "Household",
    group: "main",
    icon: HousePlus,
    showInSidebar: false,
    mobileTab: false,
  },
  {
    href: "/settings",
    label: "Account",
    pageTitle: "Account Settings",
    breadcrumbLabel: "Account",
    group: "main",
    icon: Settings2,
    showInSidebar: true,
    mobileTab: false,
    sidebarSection: "account",
    sidebarOrder: 1,
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
    sidebarSection: "admin",
    sidebarOrder: 1,
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
    sidebarSection: "admin",
    sidebarOrder: 2,
    requiredAnyScopes: ["workflow:read", "workflow:replay"],
  },
];

export const CORE_MOBILE_TABS = ROUTE_META.filter((route) => route.mobileTab);
const SIDEBAR_SECTION_META = [
  { id: "daily", title: "Daily", group: "main" },
  { id: "care", title: "Care tracking", group: "main" },
  { id: "insights", title: "Insights", group: "main" },
  { id: "account", title: "Account", group: "main" },
  { id: "admin", title: "Admin", group: "admin" },
] satisfies Array<Omit<SidebarSection, "routes">>;

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

export function getSidebarSections(group: Exclude<NavGroup, "auth">): SidebarSection[] {
  return SIDEBAR_SECTION_META.filter((section) => section.group === group)
    .map((section) => ({
      ...section,
      routes: ROUTE_META.filter(
        (route) => route.group === group && route.showInSidebar && route.sidebarSection === section.id,
      ).sort((left, right) => (left.sidebarOrder ?? 0) - (right.sidebarOrder ?? 0)),
    }))
    .filter((section) => section.routes.length > 0);
}
