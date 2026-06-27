import type { RouteRecordRaw } from "vue-router";
import { getDevUserId } from "@/api/catalog";

export const socialRoutes: RouteRecordRaw[] = [
  {
    path: "/discover",
    redirect: "/discover/feed",
  },
  {
    path: "/discover/feed",
    name: "discover-feed",
    component: () => import("@/modules/social/views/discover/DiscoverFeedView.vue"),
    meta: { shell: "workbench", module: "social", requiresAuth: true },
  },
  {
    path: "/community",
    name: "community",
    component: () => import("@/modules/social/views/CommunityView.vue"),
    meta: { shell: "workbench", module: "social", requiresAuth: true },
  },
  {
    path: "/me",
    name: "my-creator",
    redirect: () => ({ path: `/creator/${getDevUserId()}` }),
    meta: { shell: "workbench", module: "social", requiresAuth: true },
  },
];
