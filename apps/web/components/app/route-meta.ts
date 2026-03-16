import type { ComponentType, SVGProps } from "react";
import {
  Activity,
  Bell,
  ChartColumn,
  FileHeart,
  FileText,
  HeartHandshake,
  House,
  HousePlus,
  LineChart,
  LogIn,
  MessageCircle,
  Pill,
  UserPlus,
  Salad,
  Settings2,
  ShieldAlert,
  Workflow,
} from "lucide-react";
import { CompanionIcon } from "@/components/icons/companion-icon";

export type NavGroup = "main" | "admin" | "auth";
export type SidebarSectionId = "companion" | "monitoring" | "records" | "account" | "admin";

export interface RouteMeta {
  href: string;
  label: string;
  pageTitle: string;
  breadcrumbLabel: string;
  group: NavGroup;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
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
    icon: HeartHandshake,
    showInSidebar: true,
    mobileTab: false,
    sidebarSection: "records",
    sidebarOrder: 1,
  },
  {
    href: "/companion/patient-card",
    label: "Patient Card",
    pageTitle: "Patient Medical Card",
    breadcrumbLabel: "Patient Card",
    group: "main",
    icon: FileText,
    showInSidebar: false,
    mobileTab: false,
    sidebarSection: "records",
    sidebarOrder: 3,
  },
  {
    href: "/chat",
    label: "Assistant",
    pageTitle: "Companion Chat",
    breadcrumbLabel: "Chat",
    group: "main",
    icon: MessageCircle,
    showInSidebar: true,
    mobileTab: true,
    sidebarSection: "companion",
    sidebarOrder: 1,
  },
  {
    href: "/meals",
    label: "Nutrition",
    pageTitle: "Meals & Nutrition",
    breadcrumbLabel: "Meals",
    group: "main",
    icon: Salad,
    showInSidebar: true,
    mobileTab: true,
    sidebarSection: "monitoring",
    sidebarOrder: 1,
  },
  {
    href: "/medications",
    label: "Medications",
    pageTitle: "Medications",
    breadcrumbLabel: "Medications",
    group: "main",
    icon: Pill,
    showInSidebar: true,
    mobileTab: true,
    sidebarSection: "monitoring",
    sidebarOrder: 2,
  },
  {
    href: "/symptoms",
    label: "Symptoms",
    pageTitle: "Symptom Log",
    breadcrumbLabel: "Symptoms",
    group: "main",
    icon: Activity,
    showInSidebar: true,
    mobileTab: false,
    sidebarSection: "monitoring",
    sidebarOrder: 3,
  },
  {
    href: "/reports",
    label: "Lab Results",
    pageTitle: "Medical Records",
    breadcrumbLabel: "Reports",
    group: "main",
    icon: FileText,
    showInSidebar: true,
    mobileTab: false,
    sidebarSection: "records",
    sidebarOrder: 1,
  },
  {
    href: "/clinician-digest",
    label: "Clinician View",
    pageTitle: "Clinician Digest",
    breadcrumbLabel: "Clinician",
    group: "main",
    icon: FileHeart,
    showInSidebar: true,
    mobileTab: false,
    sidebarSection: "records",
    sidebarOrder: 2,
  },
  {
    href: "/dashboard",
    label: "Dashboard",
    pageTitle: "Dashboard",
    breadcrumbLabel: "Dashboard",
    group: "main",
    icon: CompanionIcon,
    showInSidebar: false,
    mobileTab: false,
  },
  {
    href: "/impact",
    label: "Impact",
    pageTitle: "Impact",
    breadcrumbLabel: "Impact",
    group: "main",
    icon: LineChart,
    showInSidebar: false,
    mobileTab: false,
  },
  {
    href: "/reminders",
    label: "Reminders",
    pageTitle: "Care Coordination",
    breadcrumbLabel: "Reminders",
    group: "main",
    icon: Bell,
    showInSidebar: true,
    mobileTab: true,
    sidebarSection: "monitoring",
    sidebarOrder: 4,
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
    showInSidebar: false,
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
    showInSidebar: false,
    mobileTab: false,
    requiredAnyScopes: ["workflow:read", "workflow:replay"],
  },
];

export const CORE_MOBILE_TABS = ROUTE_META.filter((route) => route.mobileTab);
const SIDEBAR_SECTION_META = [
  { id: "companion", title: "Care Companion", group: "main" },
  { id: "monitoring", title: "Daily Monitoring", group: "main" },
  { id: "records", title: "Medical Records", group: "main" },
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
