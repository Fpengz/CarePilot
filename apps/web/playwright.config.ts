import { defineConfig, devices } from "@playwright/test";

const backendDbPrefix = process.env.PLAYWRIGHT_SQLITE_PREFIX ?? "/tmp/dietary-playwright";

export default defineConfig({
  globalSetup: "./e2e/global-setup.ts",
  testDir: "./e2e",
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        `cd ../.. && ` +
        `AUTH_STORE_BACKEND=sqlite ` +
        `AUTH_SQLITE_DB_PATH=${backendDbPrefix}-auth.sqlite3 ` +
        `API_SQLITE_DB_PATH=${backendDbPrefix}-api.sqlite3 ` +
        `API_CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000 ` +
        `uv run python -m uvicorn apps.api.dietary_api.main:create_app --factory --host 127.0.0.1 --port 8001`,
      url: "http://127.0.0.1:8001/api/v1/health/live",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command:
        "NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001 pnpm start --hostname 127.0.0.1 --port 3000",
      url: "http://127.0.0.1:3000/login",
      cwd: ".",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
