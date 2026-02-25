import "./globals.css";
import type { Metadata } from "next";
import { HeaderSessionStatus } from "@/components/app/header-session-status";
import { HeaderNav } from "@/components/app/header-nav";
import { SessionProvider } from "@/components/app/session-provider";
import { Badge } from "@/components/ui/badge";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";

export const metadata: Metadata = {
  title: "Dietary Guardian Web",
  description: "Production web client for Dietary Guardian",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <SessionProvider>
            <div className="app-shell">
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-[color:var(--card)] focus:px-3 focus:py-2 focus:text-sm focus:shadow-lg"
          >
            Skip to main content
          </a>
          <header className="app-panel grain-overlay mb-4 overflow-hidden">
            <div className="flex flex-col gap-4 p-4 md:p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h1 className="text-xl font-semibold">Dietary Guardian</h1>
                    <Badge variant="outline">Foundation</Badge>
                  </div>
                  <p className="app-muted text-sm">Next.js + FastAPI client with account-role + scope-aware auth.</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <ThemeToggle />
                  <HeaderSessionStatus />
                </div>
              </div>
              <HeaderNav />
            </div>
          </header>
          <main id="main-content">{children}</main>
            </div>
          </SessionProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
