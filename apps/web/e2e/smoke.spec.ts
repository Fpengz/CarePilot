import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

type SessionCookie = { name: string; value: string };

const sessionCache = new Map<string, SessionCookie>();

async function fetchSessionCookie(
  request: APIRequestContext,
  email: string,
  password: string,
): Promise<SessionCookie> {
  const cacheKey = `${email}:${password}`;
  const cached = sessionCache.get(cacheKey);
  if (cached) {
    return cached;
  }
  const response = await request.post("http://127.0.0.1:8001/api/v1/auth/login", {
    data: { email, password },
  });
  if (!response.ok()) {
    throw new Error(`Login failed: ${response.status()}`);
  }
  const setCookieHeaders = response
    .headersArray()
    .filter((header) => header.name.toLowerCase() === "set-cookie")
    .map((header) => header.value);
  if (!setCookieHeaders.length) {
    throw new Error("Missing session cookie from login response");
  }
  const parsed = setCookieHeaders
    .map((header) => header.split(";")[0])
    .map((cookiePair) => cookiePair.split("="))
    .filter((parts) => parts.length >= 2)
    .map(([name, ...valueParts]) => ({ name, value: valueParts.join("=") }));
  const sessionCookie = parsed.find((cookie) => cookie.name === "dg_session") ?? parsed[0];
  if (!sessionCookie) {
    throw new Error("Missing dg_session cookie from login response");
  }
  sessionCache.set(cacheKey, sessionCookie);
  return sessionCookie;
}

async function login(
  page: Page,
  request: APIRequestContext,
  email = "member@example.com",
  password = "member-pass",
) {
  const sessionCookie = await fetchSessionCookie(request, email, password);
  await page.context().addCookies([
    {
      name: sessionCookie.name,
      value: sessionCookie.value,
      url: "http://127.0.0.1:3000",
    },
  ]);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Health Dashboard" })).toBeVisible({
    timeout: 15_000,
  });
}

test("login redirects to dashboard", async ({ page, request }) => {
  await login(page, request);
  await expect(page.getByRole("heading", { name: "Health Dashboard" })).toBeVisible({
    timeout: 15_000,
  });
});

test.describe("mobile navigation", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("opens and closes the mobile drawer", async ({ page, request }) => {
    await login(page, request);

    await page.getByRole("button", { name: "Open navigation drawer" }).click();
    await expect(page.getByRole("dialog", { name: "Navigation menu" })).toBeVisible();
    await expect(page.getByText("Primary routes and account context")).toBeVisible();

    await page.getByRole("button", { name: "Close navigation" }).click();
    await expect(page.getByRole("dialog", { name: "Navigation menu" })).toBeHidden();
  });
});

test("dashboard stays summary-focused and links out to settings", async ({ page, request }) => {
  await login(page, request);
  await expect(page.getByRole("heading", { name: "Health Dashboard" })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByLabel("Height (cm)")).toBeHidden();
  await expect(page.getByLabel("Weight (kg)")).toBeHidden();
});

test("settings page exposes guided health profile setup with advanced edit fallback", async ({ page, request }) => {
  await login(page, request);

  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Configuration" })).toBeVisible({
    timeout: 15_000,
  });

  // Tabs are used now
  await expect(page.getByRole("tab", { name: "Health Profile" })).toBeVisible({
    timeout: 15_000,
  });
  await page.getByRole("tab", { name: "Health Profile" }).click({ timeout: 15_000 });

  // Benchmark text check
  await expect(page.getByText("established")).toBeVisible({ timeout: 15_000 });

  // Default is guided
  await expect(page.getByRole("button", { name: "Continue" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByLabel("Age")).toBeVisible({ timeout: 15_000 });

  // Switch to advanced
  await page.getByRole("button", { name: "Advanced" }).click();
  await expect(page.getByRole("heading", { name: "Clinical Profile" })).toBeVisible();
  await expect(page.getByLabel("Sodium Limit (mg)")).toBeVisible();
});

test("reminder delivery settings live in settings, not the reminders page", async ({ page, request }) => {
  await login(page, request);

  await page.goto("/reminders");
  await expect(page.getByRole("heading", { name: "Delivery Settings" })).toHaveCount(0);

  await page.goto("/settings");
  await expect(page.getByRole("tab", { name: "Delivery" })).toBeVisible({ timeout: 15_000 });
  await page.getByRole("tab", { name: "Delivery" }).click({ timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Notification Channels" })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole("heading", { name: "Mobility Alerts" })).toBeVisible({
    timeout: 15_000,
  });
});

test("reminders page shows structured reminder sections", async ({ page, request }) => {
  await login(page, request);

  await page.goto("/reminders");
  // Check for the new tabs
  await expect(page.getByRole("tab", { name: "Due Today" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("tab", { name: "Schedule" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("tab", { name: "History" })).toBeVisible({ timeout: 15_000 });
});

test("caregiver household page shows a read-only care panel", async ({ page, request }) => {
  await login(page, request, "helper@example.com", "helper-pass");

  await page.goto("/household");
  await expect(page.getByRole("heading", { name: "Caregiving View" })).toBeVisible();
  await expect(page.getByText("Read-only monitoring for the selected household member.")).toBeVisible();
});

test("meals page includes weekly summary insights", async ({ page, request }) => {
  await login(page, request);

  await page.goto("/meals");
  await expect(page.getByRole("heading", { name: "Nutrition Intelligence" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Timeline" })).toBeVisible();
});

test("medications page exposes regimen and adherence tooling", async ({ page, request }) => {
  await login(page, request);

  await page.goto("/medications");
  await expect(page.getByRole("heading", { name: "Care Plan Adherence" })).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText("Clinical Adherence")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Active Regimens" })).toBeVisible({
    timeout: 15_000,
  });
});

test("medication normalization review hides after confirm", async ({ page, request }) => {
  await login(page, request);

  await page.route("**/api/v1/medications/intake/text", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        draft_id: "draft-1",
        source: { source_type: "plain_text", extracted_text: "Metformin 500mg", source_hash: "hash-1" },
        normalized_instructions: [
          {
            medication_name_raw: "Metformin",
            medication_name_canonical: "metformin",
            dosage_text: "500mg",
            timing_type: "fixed_time",
            frequency_type: "fixed_time",
            frequency_times_per_day: 1,
            offset_minutes: 0,
            slot_scope: [],
            fixed_time: "08:00",
            time_rules: [],
            duration_days: null,
            start_date: "2026-03-15",
            end_date: null,
            confidence: 0.95,
            ambiguities: [],
          },
        ],
        regimens: [],
        reminders: [],
        scheduled_notifications: [],
      }),
    });
  });

  await page.route("**/api/v1/medications/intake/confirm", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        draft_id: "draft-1",
        source: { source_type: "plain_text", extracted_text: "Metformin 500mg", source_hash: "hash-1" },
        normalized_instructions: [],
        regimens: [],
        reminders: [],
        scheduled_notifications: [],
      }),
    });
  });

  await page.goto("/medications");
  // New intake flow
  await page.getByText("Paste Text").click();
  await page.getByLabel("Instructions").fill("Metformin 500mg daily");
  await page.getByRole("button", { name: "Analyze Instructions" }).click();

  await expect(page.getByRole("heading", { name: "Normalization Review" })).toBeVisible();
  await page.getByRole("button", { name: "Confirm & Create Reminders" }).click();
  await expect(page.getByRole("heading", { name: "Normalization Review" })).toHaveCount(0);
});

test("symptoms, reports, clinical cards, and metrics pages are available", async ({ page, request }) => {
  await login(page, request);

  await page.goto("/symptoms");
  await expect(page.getByRole("heading", { name: "Symptom Monitoring" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Log Symptom Check-In" })).toBeVisible();

  await page.goto("/reports");
  await expect(page.getByRole("heading", { name: "Clinical Intelligence" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Process Medical Record" })).toBeVisible();

  await page.goto("/clinical-cards");
  await expect(page.getByRole("heading", { name: "Clinical Card Generator" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate Card" })).toBeVisible();

  await page.goto("/metrics");
  await expect(page.getByRole("heading", { name: "Daily Nutrition Overview" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Refresh Trends" })).toBeVisible();
});
