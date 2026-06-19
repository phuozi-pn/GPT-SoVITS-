import { watch } from "vue";
import { useRoute } from "vue-router";
import { getPageMeta } from "@/config/navigation";
import { setPageMeta } from "@/utils/pageMeta";

/** 根据路由同步 document.title 与 meta description */
export function useDocumentMeta() {
  const route = useRoute();

  function apply() {
    const meta = getPageMeta(route.path, typeof route.name === "string" ? route.name : null);
    const title = `${meta.label} · ${meta.group}`;
    setPageMeta(title, meta.desc);
  }

  watch(() => [route.path, route.name] as const, apply, { immediate: true });
}
