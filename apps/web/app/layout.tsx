import "./globals.css";
import type { Metadata } from "next";
import { AppShell } from "@/components/app/app-shell";
import { SessionProvider } from "@/components/app/session-provider";
import { ThemeProvider } from "@/components/theme-provider";

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
            <>
              <a
                href="#main-content"
                className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-[color:var(--card)] focus:px-3 focus:py-2 focus:text-sm focus:shadow-lg"
              >
                Skip to main content
              </a>
              <AppShell>{children}</AppShell>
            </>
          </SessionProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
