import { expect, test } from "@playwright/test";

test("login redirects to dashboard", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("member@example.com");
  await page.getByLabel("Password").fill("member-pass");
  await page.getByRole("button", { name: "Login" }).click();

  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
});

test.describe("mobile navigation", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("opens and closes the mobile drawer", async ({ page }) => {
    await page.goto("/dashboard");
    await page.getByRole("button", { name: "Open navigation drawer" }).click();
    await expect(page.getByRole("dialog", { name: "Navigation menu" })).toBeVisible();
    await expect(page.getByText("Primary routes and account context")).toBeVisible();

    await page.getByRole("button", { name: "Close navigation" }).click();
    await expect(page.getByRole("dialog", { name: "Navigation menu" })).toBeHidden();
  });
});

test("dashboard stays summary-focused and links out to settings", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("member@example.com");
  await page.getByLabel("Password").fill("member-pass");
  await page.getByRole("button", { name: "Login" }).click();

  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Today at a Glance" })).toBeVisible();
  await expect(page.getByLabel("Height (cm)")).toBeHidden();
  await expect(page.getByLabel("Weight (kg)")).toBeHidden();
  await expect(page.getByRole("link", { name: "Open Settings" })).toBeVisible();
});

test("settings page exposes guided health profile setup with advanced edit fallback", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("member@example.com");
  await page.getByLabel("Password").fill("member-pass");
  await page.getByRole("button", { name: "Login" }).click();

  await page.goto("/settings");
  await expect(page.locator("#main-content").getByRole("heading", { name: "Settings" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Guided Health Setup" })).toBeVisible();
  await expect(page.getByText("Step 1 of 5")).toBeVisible();
  await expect(page.getByRole("button", { name: "Advanced Edit" })).toBeVisible();
  await expect(page.getByLabel("Age")).toBeVisible();
  await page.getByRole("button", { name: "Advanced Edit" }).click();
  await expect(page.getByRole("heading", { name: "Advanced Health Profile" })).toBeVisible();
  await expect(page.getByLabel("Height (cm)")).toBeVisible();
  await expect(page.getByLabel("Daily protein target (g)")).toBeVisible();
  await expect(page.getByLabel("Daily fiber target (g)")).toBeVisible();
});

test("caregiver household page shows a read-only care panel", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("helper@example.com");
  await page.getByLabel("Password").fill("helper-pass");
  await page.getByRole("button", { name: "Login" }).click();

  await page.goto("/household");
  await expect(page.getByRole("heading", { name: "Caregiving View" })).toBeVisible();
  await expect(page.getByText("Read-only monitoring for the selected household member.")).toBeVisible();
});

test("meals page includes weekly summary insights", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("member@example.com");
  await page.getByLabel("Password").fill("member-pass");
  await page.getByRole("button", { name: "Login" }).click();

  await page.goto("/meals");
  await expect(page.locator("#main-content").getByRole("heading", { name: "Meal Analysis and Record Review" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Weekly Pattern Summary" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Load Weekly Summary" })).toBeVisible();
});

test("medications page exposes regimen and adherence tooling", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("member@example.com");
  await page.getByLabel("Password").fill("member-pass");
  await page.getByRole("button", { name: "Login" }).click();

  await page.goto("/medications");
  await expect(page.locator("#main-content").getByRole("heading", { name: "Medication Tracking and Adherence" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Regimen Management" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create Regimen" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Adherence Metrics" })).toBeVisible();
});

test("symptoms, reports, clinical cards, and metrics pages are available", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("member@example.com");
  await page.getByLabel("Password").fill("member-pass");
  await page.getByRole("button", { name: "Login" }).click();

  await page.goto("/symptoms");
  await expect(page.locator("#main-content").getByRole("heading", { name: "Symptom Check-Ins and Safety Triage" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Submit Check-In" })).toBeVisible();

  await page.goto("/reports");
  await expect(page.locator("#main-content").getByRole("heading", { name: "Clinical Report Parser" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Parse Report" })).toBeVisible();

  await page.goto("/clinical-cards");
  await expect(page.locator("#main-content").getByRole("heading", { name: "Clinical Card Generator" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Generate Card" })).toBeVisible();

  await page.goto("/metrics");
  await expect(page.locator("#main-content").getByRole("heading", { name: "Numerical Trend Analysis" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Refresh Trends" })).toBeVisible();
});
