import { test, expect } from "@playwright/test";

const origin = process.env.E2E_BASE_URL || "http://localhost:3000";
const sessionCookie = process.env.E2E_SESSION_COOKIE || "ecommerce_session";

test("session guards, login, refresh, CSRF, expiry and logout", async ({
  page,
  context,
}) => {
  for (const path of ["/orders", "/orders/ORD1001", "/chat"]) {
    await page.goto(path);
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("navigation")).toHaveCount(0);
  }
  await expect(
    page.getByRole("heading", { name: "Welcome back" }),
  ).toBeVisible();
  expect((await page.request.get("/api/v1/auth/me")).status()).toBe(401);
  const rejectedOrigin = await page.request.post("/api/v1/auth/login", {
    headers: { Origin: "http://127.0.0.1:3000" },
    data: { email: "invalid@example.test", password: "invalid" },
  });
  expect(rejectedOrigin.status()).toBe(403);
  await page.getByLabel("Email address").fill("alex@example.test");
  await page.getByLabel("Password", { exact: true }).fill("incorrect-password");
  await page.getByRole("button", { name: /Sign in/ }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("navigation")).toHaveCount(0);
  await page.getByLabel("Password", { exact: true }).fill("DemoShop!2026");
  await page.getByRole("button", { name: /Sign in/ }).click();
  await expect(page).toHaveURL(/\/orders$/);
  await expect(page.getByRole("navigation")).toBeVisible();
  expect((await page.request.get("/api/v1/auth/me")).status()).toBe(200);
  const cookies = await context.cookies();
  expect(cookies.find((c) => c.name === sessionCookie)?.httpOnly).toBe(
    true,
  );
  expect(cookies.find((c) => c.name === "csrf_token")?.httpOnly).toBe(false);
  expect(
    (
      await page.request.post("/api/v1/auth/logout", {
        headers: { Origin: origin },
        data: {},
      })
    ).status(),
  ).toBe(403);
  await page.reload();
  await expect(page.getByRole("heading", { name: "My orders" })).toBeVisible();
  await page.goto("/login");
  await expect(page).toHaveURL(/\/orders$/);
  await page.getByRole("link", { name: "Support assistant" }).click();
  await expect(page).toHaveURL(/\/chat$/);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("navigation")).toHaveCount(0);
  expect((await page.request.get("/api/v1/auth/me")).status()).toBe(401);
  expect(
    (await context.cookies()).some(
      (c) => c.name === sessionCookie || c.name === "csrf_token",
    ),
  ).toBe(false);
  await page.goto("/chat");
  await expect(page).toHaveURL(/\/login$/);
  await context.addCookies([
    {
      name: sessionCookie,
      value: "invalid-session",
      url: origin,
    },
  ]);
  await page.goto("/orders");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("navigation")).toHaveCount(0);
});
