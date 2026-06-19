import type { Page } from "@playwright/test";

export const E2E_CATALOG_ID = "22222222-2222-2222-2222-222222222222";

/** 音色 owner（创作者） */
export const DEV_USER_A = "00000000-0000-0000-0000-000000000001";
/** 买家 / 被授权方 */
export const DEV_USER_B = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
/** 运营审核（也可作第二买家） */
export const DEV_USER_C = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";

/** 每次购买用新 dev 用户，避免并行 E2E 因「已授权」跳过结账弹窗 */
export function ephemeralBuyerId(): string {
  return crypto.randomUUID();
}

export async function loginDevMode(page: Page, userId = DEV_USER_B) {
  await page.goto("/login");
  await page.evaluate((uid) => {
    localStorage.removeItem("access_token");
    localStorage.setItem("dev_mode", "1");
    localStorage.setItem("dev_user_id", uid);
  }, userId);
  await page.goto("/library");
}

export async function clearAppSession(page: Page) {
  await page.goto("/");
  await page.evaluate(() => localStorage.clear());
}

export async function purchaseE2eVoice(page: Page, buyerId?: string) {
  const buyer = buyerId ?? ephemeralBuyerId();
  await loginDevMode(page, buyer);
  await page.goto(`/catalog?pick=${E2E_CATALOG_ID}&intent=purchase`);
  await page.getByRole("heading", { name: "购买成功" }).waitFor({ timeout: 25_000 });
  return page;
}
