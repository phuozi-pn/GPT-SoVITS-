/**
 * 导航配置
 *
 * 侧栏分组由 architecture/modules.ts + architecture/registry.ts 派生。
 * 页面元数据 → config/page-meta.ts
 */

import { APP_MODULES, DEFAULT_WORKBENCH_ROUTE, PUBLIC_CATALOG_ROUTE } from "@/architecture/modules";
import {
  SIDEBAR_NAV_OVERRIDES,
  SIDEBAR_ROUTE_NAMES,
  type WorkbenchModuleId,
} from "@/architecture/registry";

export type NavItem = {
  to: string;
  label: string;
  hint: string;
  name: string;
  adminOnly?: boolean;
};

export type NavGroup = {
  id: string;
  label: string;
  summary: string;
  items: NavItem[];
};

/** 工作台默认路由 */
export const DEFAULT_ROUTE = DEFAULT_WORKBENCH_ROUTE;

/** 公开站点路由 */
export const PUBLIC_SITE_ROUTE = PUBLIC_CATALOG_ROUTE;

/** 重新导出页面元数据 */
export { type PageMeta, PAGE_META, resolvePageKey, getPageMeta } from "./page-meta";

function buildSidebarItems(moduleId: WorkbenchModuleId): NavItem[] {
  const mod = APP_MODULES.find((m) => m.id === moduleId);
  if (!mod) return [];

  return SIDEBAR_ROUTE_NAMES[moduleId].flatMap((routeName) => {
    const route = mod.routes.find((r) => r.name === routeName);
    if (!route) return [];
    const override = SIDEBAR_NAV_OVERRIDES[routeName];
    return [
      {
        name: override?.name ?? route.name,
        to: route.path,
        label: override?.label ?? route.label,
        hint: override?.hint ?? route.hint ?? "",
        adminOnly: route.adminOnly,
      },
    ];
  });
}

function buildNavGroup(moduleId: WorkbenchModuleId): NavGroup {
  const mod = APP_MODULES.find((m) => m.id === moduleId)!;
  return {
    id: mod.id,
    label: mod.label,
    summary: mod.summary,
    items: buildSidebarItems(moduleId),
  };
}

/** 工作台侧栏分组（不含运营） */
export const NAV_GROUPS: NavGroup[] = (["produce", "voice", "social"] as const).map(buildNavGroup);

/** 运营模块侧栏分组 */
export const ADMIN_NAV_GROUP: NavGroup = buildNavGroup("ops");

/** 构建导航分组（含可选运营模块） */
export function buildNavGroups(includeAdmin: boolean): NavGroup[] {
  if (!includeAdmin) return [...NAV_GROUPS];
  return [...NAV_GROUPS, ADMIN_NAV_GROUP];
}
