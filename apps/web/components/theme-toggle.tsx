"use client";

import { useEffect, useState } from "react";
import { Moon, Sun, SunMoon } from "lucide-react";
import { useTheme } from "next-themes";

import { Button } from "@/components/ui/button";

const THEMES = ["light", "dark", "system"] as const;
type ThemeName = (typeof THEMES)[number];

function nextTheme(theme: string | undefined): ThemeName {
  const current = THEMES.includes((theme ?? "system") as ThemeName) ? ((theme ?? "system") as ThemeName) : "system";
  const index = THEMES.indexOf(current);
  return THEMES[(index + 1) % THEMES.length];
}

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const active = ((mounted ? theme : "system") ?? "system") as ThemeName;
  const Icon = active === "light" ? Sun : active === "dark" ? Moon : SunMoon;
  const effective = mounted ? (active === "system" ? resolvedTheme ?? "light" : active) : "system";

  return (
    <Button
      type="button"
      variant="secondary"
      size="sm"
      aria-label={`Theme: ${active}. Activate to switch theme.`}
      title={`Theme: ${active} (${effective})`}
      onClick={() => setTheme(nextTheme(theme))}
      className="min-w-28 justify-start"
    >
      <Icon className="h-4 w-4" aria-hidden />
      <span className="capitalize">{active}</span>
    </Button>
  );
}
