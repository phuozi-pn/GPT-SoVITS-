import { computed, type ComputedRef } from "vue";
import { useRoute } from "vue-router";
import type { AppShell } from "@/architecture/modules";
import { hasAppSession } from "@/utils/session";

export function useAppShell(): ComputedRef<AppShell> {
  const route = useRoute();
  return computed(() => {
    const shell = route.meta.shell as AppShell | undefined;
    if (shell === "bare" || shell === "public" || shell === "workbench") {
      return shell;
    }
    if (route.meta.public && !hasAppSession()) return "public";
    return "workbench";
  });
}

export function useIsPublicVisitor(): ComputedRef<boolean> {
  const shell = useAppShell();
  return computed(() => shell.value === "public");
}

/** @deprecated 使用 useIsPublicVisitor */
export const useIsShowcaseVisitor = useIsPublicVisitor;
