import { test, expect } from "@playwright/test";
test("login, status, prepare, keep, prepare, confirm, updated order", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByLabel("Email address").fill("alex@example.test");
  await page.getByLabel("Password", { exact: true }).fill("DemoShop!2026");
  await page.getByRole("button", { name: "Sign in →" }).click();
  await expect(page.getByRole("heading", { name: "My orders" })).toBeVisible();
  await page.screenshot({path:'test-results/orders-desktop.png',fullPage:true});
  await page.getByRole("link", { name: "Support assistant" }).click();
  await page
    .getByLabel("Message the support assistant")
    .fill("Where is my order ORD1001?");
  await page.getByRole("button", { name: "Send ↑" }).click();
  await expect(
    page.getByText(/ORD1001 · Studio headphones is SHIPPED/),
  ).toBeVisible();
  await page
    .getByLabel("Message the support assistant")
    .fill("Please cancel ORD1004");
  await page.getByRole("button", { name: "Send ↑" }).click();
  await page.getByRole("button", { name: "Keep order" }).click();
  await expect(page.getByText(/This request is closed/)).toBeVisible();
  await page
    .getByLabel("Message the support assistant")
    .fill("Please cancel ORD1004");
  await page.getByRole("button", { name: "Send ↑" }).click();
  await page.getByRole("button", { name: "Confirm cancellation" }).click();
  await expect(page.getByText("Your order is cancelled.")).toBeVisible();
  await page.screenshot({path:'test-results/chat-confirmed.png',fullPage:true});
  await page.goto("/orders/ORD1004");
  await expect(page.locator(".badge")).toHaveText("cancelled");
  await page.setViewportSize({width:390,height:844});
  await expect(page.getByRole('button',{name:'Sign out'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:'test-results/order-mobile.png',fullPage:true});
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome back" }),
  ).toBeVisible();
});
