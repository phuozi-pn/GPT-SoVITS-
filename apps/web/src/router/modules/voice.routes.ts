import type { RouteRecordRaw } from "vue-router";

export const voiceRoutes: RouteRecordRaw[] = [
  {
    path: "/studio",
    name: "studio",
    component: () => import("@/modules/voice/views/StudioView.vue"),
    meta: { shell: "workbench", module: "voice", requiresAuth: true },
  },
  {
    path: "/voices",
    name: "voices",
    component: () => import("@/modules/voice/views/VoicesView.vue"),
    meta: { shell: "workbench", module: "voice", requiresAuth: true },
  },
  {
    path: "/catalog",
    name: "catalog",
    component: () => import("@/modules/voice/views/CatalogView.vue"),
    meta: { shell: "workbench", module: "voice", requiresAuth: true },
  },
  {
    path: "/kyc",
    name: "kyc",
    component: () => import("@/modules/voice/views/KycView.vue"),
    meta: { shell: "workbench", module: "voice", requiresAuth: true },
  },
  {
    path: "/quality/:voiceVersionId",
    name: "quality",
    component: () => import("@/modules/voice/views/QualityView.vue"),
    meta: { shell: "workbench", module: "voice", requiresAuth: true },
  },
];
