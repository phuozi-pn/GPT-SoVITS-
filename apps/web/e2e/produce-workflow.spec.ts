import { expect, test } from "@playwright/test";
import { DEV_USER_B, loginDevMode } from "./fixtures";

test.describe("金路径 · 制作", () => {
  test.beforeEach(async ({ page }) => {
    await loginDevMode(page, DEV_USER_B);
  });

  test("智能配音工作台与场景切换", async ({ page }) => {
    await page.goto("/library");
    await expect(page.getByRole("tab", { name: /单人朗读/ })).toBeVisible();
    await expect(page.getByRole("tab", { name: /多人情景/ })).toBeVisible();
    await page.getByRole("tab", { name: /多人情景/ }).click();
    await expect(page.getByRole("button", { name: "多人情景" })).toBeVisible();
    await expect(page.getByRole("link", { name: "短剧批量配音" }).first()).toBeVisible();
  });

  test("短剧批量页结构与模板", async ({ page }) => {
    await page.goto("/projects");
    await expect(page.getByRole("button", { name: "新建项目" })).toBeVisible();
    await expect(page.getByText("CSV 批量合成")).toBeVisible();
    await expect(page.getByRole("link", { name: "下载模板" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "智能配音" }).first()).toBeVisible();
  });

  test("制作模块互跳", async ({ page }) => {
    await page.goto("/library");
    await page.getByRole("link", { name: "短剧批量配音" }).first().click();
    await expect(page).toHaveURL(/\/projects/);
    await page.getByRole("link", { name: "智能配音" }).first().click();
    await expect(page).toHaveURL(/\/library/);
  });
});

test.describe("金路径 · 训练工作台", () => {
  test.beforeEach(async ({ page }) => {
    await loginDevMode(page, DEV_USER_B);
  });

  test("训练四步流水线可见", async ({ page }) => {
    await page.goto("/studio");
    await expect(page.getByText("创建音色")).toBeVisible();
    await expect(page.getByText("上传素材")).toBeVisible();
    await expect(page.getByText("训练音色")).toBeVisible();
    await expect(page.getByText("合成试听")).toBeVisible();
  });

  test("无音色时智能配音引导训练", async ({ page }) => {
    await page.goto("/library");
    const trainLink = page.getByRole("link", { name: "去训练工作台" });
    if (await trainLink.isVisible().catch(() => false)) {
      await trainLink.click();
      await expect(page).toHaveURL(/\/studio/);
    }
  });
});

test.describe("金路径 · 端到端旅程", () => {
  test("访客 → 登录 → 制作 → 训练入口", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Phonia" })).toBeVisible();
    await expect(page.getByText("短剧文本配音")).toBeVisible();

    await page.getByRole("button", { name: /登录并开始|进入工作台/ }).click();
    await expect(page).toHaveURL(/\/login/);

    await page.getByRole("button", { name: "跳过登录（开发模式）" }).click();
    await expect(page).toHaveURL(/\/library/);

    await page.getByRole("link", { name: "训练工作台" }).first().click();
    await expect(page).toHaveURL(/\/studio/);
  });
});
