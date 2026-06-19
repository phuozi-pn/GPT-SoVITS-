/** 是否已进入工作台会话（登录或开发模式） */
export function hasAppSession(): boolean {
  return !!localStorage.getItem("access_token") || localStorage.getItem("dev_mode") === "1";
}
