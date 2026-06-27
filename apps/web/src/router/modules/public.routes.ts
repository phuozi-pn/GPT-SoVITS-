import type { RouteRecordRaw } from "vue-router";

export const publicRoutes: RouteRecordRaw[] = [
  {
    path: "/splash",
    name: "splash",
    component: () => import("@/modules/public/views/SplashView.vue"),
    meta: { shell: "bare", public: true },
  },
  {
    path: "/",
    name: "home",
    component: () => import("@/modules/public/views/HomeView.vue"),
    meta: { shell: "public", public: true },
  },
  {
    path: "/browse",
    name: "browse",
    component: () => import("@/modules/voice/views/PublicCatalogView.vue"),
    meta: { shell: "public", module: "voice", public: true },
  },
  {
    path: "/updates",
    name: "public-feed",
    component: () => import("@/modules/social/views/PublicDiscoverView.vue"),
    meta: { shell: "public", module: "social", public: true },
  },
  {
    path: "/login",
    name: "login",
    component: () => import("@/modules/public/views/LoginView.vue"),
    meta: { shell: "bare", public: true },
  },
  {
    path: "/verify/:authorizationId",
    name: "verify",
    component: () => import("@/modules/public/views/VerifyView.vue"),
    meta: { shell: "bare", public: true },
  },
  {
    path: "/creator/:userId",
    name: "creator",
    component: () => import("@/modules/social/views/CreatorView.vue"),
    meta: { module: "social", public: true },
  },
  {
    path: "/creators",
    name: "creators",
    component: () => import("@/modules/social/views/CreatorsBrowseView.vue"),
    meta: { module: "social", public: true },
  },
];
