/** @type {import('next').NextConfig} */

const nextConfig = {
  reactStrictMode: true,
  eslint: {
    ignoreDuringBuilds: true,
  },
  env: {
    NEXT_PUBLIC_APP_TIMEZONE: process.env.APP_TIMEZONE || "Asia/Singapore",
  },
};

export default nextConfig;
