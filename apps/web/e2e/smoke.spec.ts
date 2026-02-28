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

test("dashboard shows adaptive agent controls", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("member@example.com");
  await page.getByLabel("Password").fill("member-pass");
  await page.getByRole("button", { name: "Login" }).click();

  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Adaptive Daily Meal Agent" })).toBeVisible();
  await expect(page.getByLabel("Height (cm)")).toBeVisible();
  await expect(page.getByLabel("Weight (kg)")).toBeVisible();
  await expect(page.getByRole("button", { name: "Refresh Agent Feed" })).toBeVisible();
});
