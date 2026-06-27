import { expect, test } from "@playwright/test";
import { DEV_USER_B, E2E_CATALOG_ID, ephemeralBuyerId, loginDevMode } from "./fixtures";

test.describe("金路径 · 展示站", () => {
  test("访客首页叙事与指标区", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Phonia" })).toBeVisible();
    await expect(page.getByRole("button", { name: /浏览公开音色|登录并开始/ })).toBeVisible();
  });

  test("公开音色馆可访问", async ({ page }) => {
    await page.goto("/browse");
    await expect(page.getByRole("heading", { name: "公开音色馆" })).toBeVisible();
  });

  test("社区动态公开页", async ({ page }) => {
    await page.goto("/updates");
    await expect(page.getByRole("heading", { name: "社区动态" })).toBeVisible();
  });

  test("未登录访问工作台跳转登录", async ({ page }) => {
    await page.goto("/library");
    await expect(page).toHaveURL(/\/login/);
  });

  test("browse 支持 pick 深链参数", async ({ page }) => {
    await page.goto(`/browse?pick=${E2E_CATALOG_ID}`);
    await expect(page).toHaveURL(/pick=/);
  });

  test("公开馆购买登录保留 pick 与 intent", async ({ page }) => {
    await page.goto(`/browse?pick=${E2E_CATALOG_ID}`);
    const loginBtn = page.getByRole("button", { name: "登录后购买 / 合成" });
    await expect(loginBtn).toBeVisible({ timeout: 15_000 });
    await loginBtn.click();
    await expect(page).toHaveURL(/\/login/);
    await expect(page).toHaveURL(/intent=purchase/);
    await expect(page).toHaveURL(/pick=/);
  });

  test("登录回跳音色馆保留深链", async ({ page }) => {
    await page.goto(`/login?redirect=/catalog&pick=${E2E_CATALOG_ID}&intent=purchase`);
    await page.getByRole("button", { name: "跳过登录（开发模式）" }).click();
    await expect(page).toHaveURL(/\/catalog/);
    await expect(page).toHaveURL(/pick=/);
  });
});

test.describe("金路径 · API 联调", () => {
  test.beforeEach(async ({ page }) => {
    await loginDevMode(page, DEV_USER_B);
  });

  test("公开馆展示 E2E 种子音色", async ({ page }) => {
    await page.goto(`/browse?pick=${E2E_CATALOG_ID}`);
    await expect(page.getByRole("heading", { name: "龙渊 · 沉稳男声" })).toBeVisible({ timeout: 15_000 });
  });

  test("购买 mock 弹出成功并进入合成", async ({ page }) => {
    const buyerId = ephemeralBuyerId();
    await loginDevMode(page, buyerId);
    await page.goto(`/catalog?pick=${E2E_CATALOG_ID}&intent=purchase`);
    await expect(page.getByRole("heading", { name: "购买成功" })).toBeVisible({ timeout: 25_000 });
    await page.getByRole("button", { name: "立即试听合成" }).click();
    await expect(page.locator(".make-action-bar__cta")).toBeVisible();
  });
});
