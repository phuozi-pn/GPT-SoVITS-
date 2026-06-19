import type { RouteRecordRaw } from "vue-router";

export const opsRoutes: RouteRecordRaw[] = [
  {
    path: "/admin",
    name: "admin",
    component: () => import("@/modules/ops/views/AdminView.vue"),
    meta: { shell: "workbench", module: "ops", requiresAuth: true, requiresAdmin: true, labs: true },
  },
];
