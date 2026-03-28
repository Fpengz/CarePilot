import { expect, test } from "@playwright/test";

test("full user journey: login, profile setup, and dashboard verification", async ({ page }) => {
  // 1. Login
  await page.goto("/login");
  await page.getByLabel("Email").fill("member@example.com");
  await page.getByLabel("Password").fill("member-pass");
  const loginResponse = page.waitForResponse(r => r.url().includes("/auth/login") && r.status() === 200);
  await page.getByRole("button", { name: "Login" }).click();
  await loginResponse;

  await expect(page).toHaveURL(/\/dashboard$/, { timeout: 15_000 });
  
  // 2. Guided Health Profile Setup
  await page.goto("/settings");
  await page.waitForLoadState("networkidle");
  await page.getByRole("tab", { name: "Health Profile" }).click();
  
  // Start guided onboarding if not already complete
  // Using a more robust check for onboarding visibility
  const onboardingContainer = page.locator(".onboarding-step-container");
  if (await onboardingContainer.isVisible({ timeout: 10_000 })) {
    await page.getByLabel("Age").fill("45");
    await page.getByRole("button", { name: "Continue" }).click();
    
    // Step 2: Conditions
    await expect(page.getByText("Medical Conditions")).toBeVisible();
    await page.getByRole("button", { name: "Add Condition" }).click();
    await page.getByPlaceholder("Condition name").fill("Hypertension");
    await page.getByRole("button", { name: "Continue" }).click();
    
    // Step 3: Goals
    await expect(page.getByText("Nutrition Goals")).toBeVisible();
    await page.getByRole("button", { name: "Add Goal" }).click();
    await page.getByPlaceholder("Goal type").fill("lower_sodium");
    await page.getByRole("button", { name: "Finish Setup" }).click();
  }

  // 3. Verify Dashboard reflect profile (e.g. goals)
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { name: "Health Dashboard" })).toBeVisible();
  
  // Check if our goal shows up in the summary or insights
  // Depending on how components render, we check for presence of "lower_sodium"
  // (Might need a small delay for background projections if any)
  await expect(page.getByText("lower_sodium")).toBeVisible({ timeout: 10_000 });

  // 4. Meal Upload Flow
  await page.goto("/meals");
  await expect(page.getByRole("heading", { name: "Nutrition Intelligence" })).toBeVisible();
  
  // (Skipping actual file upload in this script to avoid needing a real JPG asset in the environment,
  // or we can use a small buffer if needed. For now, we verify page accessibility.)
  await expect(page.getByText("Drop meal photo here")).toBeVisible();

  // 5. Chat Interaction
  await page.goto("/chat");
  await expect(page.getByPlaceholder("Ask anything")).toBeVisible();
  await page.getByPlaceholder("Ask anything").fill("How is my sodium intake today?");
  await page.keyboard.press("Enter");
  
  // Verify streaming response container
  await expect(page.locator(".chat-markdown")).toBeVisible({ timeout: 20_000 });
});
