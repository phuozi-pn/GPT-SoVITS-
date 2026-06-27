/** 是否已进入工作台会话（登录或开发模式） */
export function hasAppSession(): boolean {
  return !!localStorage.getItem("access_token") || localStorage.getItem("dev_mode") === "1";
}

/** 清除登录 / 开发模式会话 */
export function clearAppSession(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("dev_mode");
  localStorage.removeItem("user_phone");
  localStorage.removeItem("user_email");
}
