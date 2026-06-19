import { createRouter, createWebHistory } from "vue-router";
import { registerRouterGuards } from "@/router/guards";
import { opsRoutes } from "@/router/modules/ops.routes";
import { produceRoutes } from "@/router/modules/produce.routes";
import { publicRoutes } from "@/router/modules/public.routes";
import { socialRoutes } from "@/router/modules/social.routes";
import { voiceRoutes } from "@/router/modules/voice.routes";

const router = createRouter({
  history: createWebHistory(),
  routes: [...publicRoutes, ...produceRoutes, ...voiceRoutes, ...socialRoutes, ...opsRoutes],
});

registerRouterGuards(router);

export default router;
