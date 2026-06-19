/**
 * 功能开关 — 默认开放所有功能，设置 VITE_LABS=0 可关闭实验功能
 *
 * @see docs/architecture/2026-06-19-对外演示路径冻结.md
 */

/** 默认为 true（开放）；设为 `"0"` 时隐藏运营台、支付订单、卖家钱包等实验入口 */
export const isLabsEnabled = (): boolean => import.meta.env.VITE_LABS !== "0";

/** 对外演示冻结的三条用户故事（路由锚点） */
export const DEMO_STORIES = [
  {
    id: "visitor",
    title: "访客试听",
    path: "/browse",
    steps: ["首页 /", "公开音色馆 /browse", "登录"],
  },
  {
    id: "buyer",
    title: "买家授权合成",
    path: "/catalog",
    steps: ["音色馆 /catalog", "购买授权", "文本转语音 /library", "验真 /verify/:id"],
  },
  {
    id: "creator",
    title: "创作者上架",
    path: "/studio",
    steps: ["训练 /studio", "音色馆发布", "社区动态 /discover/feed"],
  },
] as const;

/** Labs 路由：未开启 VITE_LABS 时从导航与直链拦截 */
export const LABS_ROUTE_NAMES = new Set(["admin"]);
