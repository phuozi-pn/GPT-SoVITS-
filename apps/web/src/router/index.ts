import { createRouter, createWebHistory } from "vue-router";
import LoginView from "@/views/LoginView.vue";
import StudioView from "@/views/StudioView.vue";
import LibraryView from "@/views/LibraryView.vue";
import CatalogView from "@/views/CatalogView.vue";
import ProjectView from "@/views/ProjectView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/studio" },
    { path: "/login", name: "login", component: LoginView },
    { path: "/studio", name: "studio", component: StudioView, meta: { requiresAuth: true } },
    { path: "/library", name: "library", component: LibraryView, meta: { requiresAuth: true } },
    { path: "/catalog", name: "catalog", component: CatalogView, meta: { requiresAuth: true } },
    { path: "/projects", name: "projects", component: ProjectView, meta: { requiresAuth: true } },
  ],
});

router.beforeEach((to) => {
  const token = localStorage.getItem("access_token");
  const devMode = localStorage.getItem("dev_mode") === "1";
  if (to.meta.requiresAuth && !token && !devMode) {
    return { name: "login" };
  }
  return true;
});

export default router;
