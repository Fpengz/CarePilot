import type { NextConfig } from "next";

function normalizeAllowedDevOrigins(rawOrigins: string): string[] {
  const origins = new Set<string>();
  for (const token of rawOrigins.split(",")) {
    const value = token.trim();
    if (!value) continue;
    try {
      const parsed = new URL(value);
      origins.add(parsed.hostname);
      continue;
    } catch {
      // If it's not a URL, keep a hostname-ish token and strip optional protocol/path.
      origins.add(value.replace(/^https?:\/\//, "").replace(/\/.*$/, ""));
    }
  }
  return [...origins];
}

const allowedDevOrigins = normalizeAllowedDevOrigins(
  process.env.NEXT_ALLOWED_DEV_ORIGINS ?? "http://localhost:3000,http://127.0.0.1:3000"
);

const nextConfig: NextConfig = {
  reactStrictMode: true,
  allowedDevOrigins,
};

export default nextConfig;
