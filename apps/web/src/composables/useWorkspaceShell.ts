/**
 * 工作台 Shell 状态管理
 *
 * 从 AppLayout.vue 提取，管理侧栏导航、开发模式、用户状态等。
 */
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { DEV_ADMIN_USER_ID, DEV_USER_PRESETS, getDevUserId, setDevUserId } from "@/api/catalog";
import { useUnreadMessages } from "@/composables/useUnreadMessages";
import type { NavItem, NavGroup } from "@/config/navigation";
import { buildNavGroups } from "@/config/navigation";

export function useWorkspaceShell() {
  const route = useRoute();
  const { unreadTotal } = useUnreadMessages();

  const isLogin = computed(() => route.name === "login");
  const userPhone = computed(() => localStorage.getItem("user_phone") ?? "");
  const devMode = computed(() => localStorage.getItem("dev_mode") === "1");
  const isAdmin = computed(() => getDevUserId() === DEV_ADMIN_USER_ID);

  const devUserId = computed({
    get: () => getDevUserId(),
    set: (id: string) => {
      setDevUserId(id);
      window.location.reload();
    },
  });

  const devUserLabel = computed(
    () => DEV_USER_PRESETS.find((u) => u.id === devUserId.value)?.label ?? "调试用户",
  );

  const navGroups = computed<NavGroup[]>(() => buildNavGroups(isAdmin.value));

  function isActive(item: NavItem): boolean {
    if (item.name === "discover") {
      return route.path.startsWith("/discover");
    }
    return route.path === item.to || route.path.startsWith(`${item.to}/`);
  }

  return {
    isLogin,
    userPhone,
    devMode,
    isAdmin,
    devUserId,
    devUserLabel,
    navGroups,
    unreadTotal,
    isActive,
    DEV_USER_PRESETS,
  };
}
