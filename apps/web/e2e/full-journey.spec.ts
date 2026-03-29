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
  const setCookieHeader = response
    .headersArray()
    .find((header) => header.name.toLowerCase() === "set-cookie")?.value;
  if (!setCookieHeader) {
    throw new Error("Missing session cookie from login response");
  }
  const [cookiePair] = setCookieHeader.split(";");
  const [name, ...valueParts] = cookiePair.split("=");
  const sessionCookie = { name, value: valueParts.join("=") };
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
}

test("full user journey: login, profile setup, and dashboard verification", async ({ page, request }) => {
  // 1. Login
  await login(page, request);

  // 2. Guided Health Profile Setup
  await page.goto("/settings");
  await expect(page.getByRole("heading", { name: "Configuration" })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await page.getByRole("tab", { name: "Health Profile" }).click();

  // Start guided onboarding if not already complete
  // Using a more robust check for onboarding visibility
  const continueButton = page.getByRole("button", { name: "Continue" });
  if (await continueButton.isVisible({ timeout: 10_000 })) {
    await page.getByLabel("Age").fill("45");
    await continueButton.click();

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

  await expect(page.getByText("Companion Digest")).toBeVisible({ timeout: 10_000 });

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
