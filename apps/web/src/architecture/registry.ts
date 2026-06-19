/**
 * 全栈模块注册表 — 路由、API 客户端、领域包对齐
 *
 * 与后端 apps/api/architecture/modules.py、domains/architecture.py 保持同一五分法：
 *   platform | produce | voice | social | ops
 *
 * 前端用户可见模块为 produce / voice / social / ops（platform 为横切基础设施）。
 */

import type { AppModuleId } from "./modules";

export type WorkbenchModuleId = Exclude<AppModuleId, "public">;

/** 前端 API 客户端文件 → 业务模块 */
export const API_CLIENT_MODULES: Record<string, WorkbenchModuleId | "platform"> = {
  client: "platform",
  library: "produce",
  script: "produce",
  voices: "voice",
  catalog: "voice",
  kyc: "voice",
  quality: "voice",
  settlement: "voice",
  social: "social",
  community: "social",
  admin: "ops",
};

/** 模块内 composables 路径（自包含逻辑） */
export const MODULE_COMPOSABLES: Record<WorkbenchModuleId, readonly string[]> = {
  produce: [],
  voice: ["useCatalogBrowse", "useCatalogManage", "useCatalogSynth"],
  social: ["useCommunityFeed", "useCommunityInbox", "useDiscoverCompose"],
  ops: [],
};

/** 后端 OpenAPI tag → 业务模块（与 router_registry 一致） */
export const OPENAPI_TAG_MODULES: Record<string, WorkbenchModuleId | "platform"> = {
  auth: "platform",
  usage: "platform",
  jobs: "platform",
  exports: "platform",
  synthesis: "produce",
  script: "produce",
  projects: "produce",
  voices: "voice",
  assets: "voice",
  consents: "voice",
  catalog: "voice",
  licensing: "voice",
  kyc: "voice",
  quality: "voice",
  payments: "voice",
  settlement: "voice",
  social: "social",
  community: "social",
  admin: "ops",
  developer: "ops",
  open: "ops",
};

/** 侧栏展示的路由 name（顺序固定）；未列入者为二级/外链页 */
export const SIDEBAR_ROUTE_NAMES: Record<WorkbenchModuleId, readonly string[]> = {
  produce: ["library", "projects"],
  voice: ["studio", "voices", "catalog"],
  social: ["discover-feed", "community"],
  ops: ["admin"],
};

/** 侧栏项 label/hint 覆盖（路由 name → 展示） */
export const SIDEBAR_NAV_OVERRIDES: Partial<
  Record<string, { name?: string; label?: string; hint?: string }>
> = {
  "discover-feed": { name: "discover", label: "发现", hint: "动态·精选·指南" },
};

export function moduleForApiClient(filename: string): WorkbenchModuleId | "platform" | undefined {
  const base = filename.replace(/\.ts$/, "");
  return API_CLIENT_MODULES[base];
}
