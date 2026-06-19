/**
 * 前端模块化信息架构 — 单一数据源
 *
 * 三层壳：
 *  - public：访客（未登录或显式公开页）
 *  - workbench：登录后工作台
 *  - bare：无壳（登录页、验真页）
 *
 * 五大业务模块：public | produce | voice | social | ops
 */

export type AppShell = "public" | "workbench" | "bare";

export type AppModuleId = "public" | "produce" | "voice" | "social" | "ops";

export type ModuleRoute = {
  name: string;
  path: string;
  label: string;
  hint?: string;
  /** 登录后可访问的镜像路径（公开页 ↔ 工作台页） */
  appPath?: string;
  requiresAuth?: boolean;
  adminOnly?: boolean;
  labs?: boolean;
};

export type AppModule = {
  id: AppModuleId;
  label: string;
  summary: string;
  routes: ModuleRoute[];
};

/** 访客站导航（顶栏） */
export const PUBLIC_NAV = [
  { path: "/", label: "首页", name: "home" },
  { path: "/browse", label: "音色馆", name: "browse" },
  { path: "/updates", label: "社区", name: "public-feed" },
] as const;

export const APP_MODULES: AppModule[] = [
  {
    id: "produce",
    label: "制作",
    summary: "短剧批量 · 多人情景 · 歌曲分段（规划）",
    routes: [
      {
        name: "library",
        path: "/library",
        label: "智能配音",
        hint: "单人 / 多人情景",
        requiresAuth: true,
      },
      {
        name: "projects",
        path: "/projects",
        label: "短剧批量配音",
        hint: "CSV 多角色出片",
        requiresAuth: true,
      },
    ],
  },
  {
    id: "voice",
    label: "音色",
    summary: "获取与管理可用音色",
    routes: [
      { name: "studio", path: "/studio", label: "训练工作台", hint: "授权·上传·训练", requiresAuth: true },
      { name: "voices", path: "/voices", label: "我的音色", hint: "管理自有音色", requiresAuth: true },
      {
        name: "catalog",
        path: "/catalog",
        label: "音色馆",
        hint: "试听·购买授权",
        requiresAuth: true,
        appPath: "/catalog",
      },
      { name: "browse", path: "/browse", label: "公开音色馆", hint: "访客试听", appPath: "/catalog" },
      { name: "kyc", path: "/kyc", label: "实名认证", requiresAuth: true },
      { name: "quality", path: "/quality/:voiceVersionId", label: "相似度评测", requiresAuth: true },
    ],
  },
  {
    id: "social",
    label: "社区",
    summary: "发现创作者与洽谈合作",
    routes: [
      { name: "discover-feed", path: "/discover/feed", label: "动态", hint: "时间线", requiresAuth: true },
      { name: "public-feed", path: "/updates", label: "公开动态", appPath: "/discover/feed" },
      { name: "community", path: "/community", label: "消息", hint: "私信收件箱", requiresAuth: true },
      { name: "creator", path: "/creator/:userId", label: "创作者主页" },
    ],
  },
  {
    id: "ops",
    label: "运营",
    summary: "审核与运维",
    routes: [
      { name: "admin", path: "/admin", label: "运营台", requiresAuth: true, adminOnly: true, labs: true },
    ],
  },
];

export const DEFAULT_WORKBENCH_ROUTE = "/library";

export const PUBLIC_CATALOG_ROUTE = "/browse";

export function findModuleByRouteName(name: string): AppModule | undefined {
  return APP_MODULES.find((m) => m.routes.some((r) => r.name === name));
}
