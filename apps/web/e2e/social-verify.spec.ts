import { expect, test } from "@playwright/test";
import {
  clearAppSession,
  DEV_USER_A,
  loginDevMode,
  purchaseE2eVoice,
} from "./fixtures";

test.describe("金路径 · 社区发帖", () => {
  test("发现页发帖后出现在时间线", async ({ page }) => {
    const body = `E2E 金路径帖子 ${Date.now()}`;
    await loginDevMode(page, DEV_USER_A);
    await page.goto("/discover/feed");

    await page.getByPlaceholder("分享制作心得、授权问题、或音色使用技巧…").fill(body);
    await page.getByRole("button", { name: "发布" }).click();

    await expect(page.getByText(body)).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("动态").first()).toBeVisible();
  });

  test("公开动态页可读帖子", async ({ page }) => {
    const body = `E2E 公开流帖子 ${Date.now()}`;
    await loginDevMode(page, DEV_USER_A);
    await page.goto("/discover/feed");
    await page.getByPlaceholder("分享制作心得、授权问题、或音色使用技巧…").fill(body);
    await page.getByRole("button", { name: "发布" }).click();
    await expect(page.getByText(body)).toBeVisible({ timeout: 15_000 });

    await clearAppSession(page);
    await page.goto("/updates");
    await expect(page.getByText(body)).toBeVisible({ timeout: 15_000 });
  });
});

test.describe("金路径 · 购买与验真", () => {
  test("买家购买后可验真（工作台）", async ({ page }) => {
    await purchaseE2eVoice(page);
    await page.getByRole("link", { name: "授权验真" }).click();
    await expect(page).toHaveURL(/\/verify\//);
    await expect(page.getByText("授权有效")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("龙渊 · 沉稳男声")).toBeVisible();
  });

  test("访客可读取验真结果", async ({ page, context }) => {
    await purchaseE2eVoice(page);
    const verifyHref = await page.getByRole("link", { name: "授权验真" }).getAttribute("href");
    expect(verifyHref).toMatch(/\/verify\//);

    const guest = await context.newPage();
    await guest.goto("/");
    await clearAppSession(guest);
    await guest.goto(verifyHref!);
    await expect(guest.getByText("授权有效")).toBeVisible({ timeout: 15_000 });
    await expect(guest.getByText("龙渊 · 沉稳男声")).toBeVisible();
    await guest.close();
  });

  test("我的授权列表含验真入口", async ({ page }) => {
    await purchaseE2eVoice(page);
    const checkout = page.getByRole("dialog", { name: "购买成功" });
    await checkout.getByRole("button", { name: "关闭", exact: true }).last().click();
    await page.getByRole("button", { name: "我的授权" }).click();
    const auths = page.getByRole("dialog", { name: "我的音色授权" });
    await expect(auths.getByText(/龙渊 · 沉稳男声 · active/)).toBeVisible();
    await auths.getByRole("link", { name: "验真" }).click();
    await expect(page.getByText("授权有效")).toBeVisible({ timeout: 15_000 });
  });
});
