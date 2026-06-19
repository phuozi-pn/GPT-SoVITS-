import type { Router } from "vue-router";
import { DEV_ADMIN_USER_ID, getDevUserId } from "@/api/catalog";
import { isLabsEnabled, LABS_ROUTE_NAMES } from "@/config/features";

const SPLASH_KEY = "phonia_splash_seen";

export function isAuthed(): boolean {
  return Boolean(localStorage.getItem("access_token") || localStorage.getItem("dev_mode") === "1");
}

export function registerRouterGuards(router: Router) {
  router.beforeEach((to) => {
    const authed = isAuthed();

    // 首次访问且未看过序章 → 重定向到 /splash
    if (to.path === "/" && !authed && !localStorage.getItem(SPLASH_KEY)) {
      localStorage.setItem(SPLASH_KEY, "1");
      return { name: "splash" };
    }

    if (to.meta.requiresAuth && !authed) {
      return { name: "login", query: { redirect: to.fullPath } };
    }

    if (to.meta.requiresAdmin && getDevUserId() !== DEV_ADMIN_USER_ID) {
      return { path: "/library" };
    }

    if (!isLabsEnabled() && to.name && LABS_ROUTE_NAMES.has(String(to.name))) {
      return { path: "/library" };
    }

    return true;
  });
}
