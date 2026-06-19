import type { RouteRecordRaw } from "vue-router";

export const produceRoutes: RouteRecordRaw[] = [
  {
    path: "/library",
    name: "library",
    component: () => import("@/modules/produce/views/LibraryView.vue"),
    meta: { shell: "workbench", module: "produce", requiresAuth: true },
  },
  {
    path: "/projects",
    name: "projects",
    component: () => import("@/modules/produce/views/ProjectView.vue"),
    meta: { shell: "workbench", module: "produce", requiresAuth: true },
  },
];
