import { computed, ref, watch, type Ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchCatalog, fetchCatalogTags, type CatalogEntry } from "@/api/catalog";
import { formatApiError } from "@/utils/apiErrors";
import { parseCatalogTags } from "@/utils/catalogDisplay";

export function useCatalogBrowse() {
  const route = useRoute();
  const router = useRouter();

  const entries = ref<CatalogEntry[]>([]);
  const availableTags = ref<string[]>([]);
  const selectedTags = ref<string[]>([]);
  const tagQuery = ref("");
  const selectedCatalogId = ref("");
  const viewMode = ref<"featured" | "all">("featured");
  const loading = ref(false);
  const error = ref("");
  const success = ref("");

  const featuredList = computed(() => entries.value.filter((e) => e.featured));
  const otherList = computed(() => entries.value.filter((e) => !e.featured));

  const heroEntries = computed(() => {
    if (!entries.value.length) return [];
    if (selectedTags.value.length) return entries.value.filter((e) => e.featured);
    if (featuredList.value.length) return featuredList.value;
    return [entries.value[0]];
  });

  const gridEntries = computed(() => {
    if (!entries.value.length) return [];
    if (selectedTags.value.length) {
      const heroIds = new Set(heroEntries.value.map((e) => e.catalog_id));
      return entries.value.filter((e) => !heroIds.has(e.catalog_id));
    }
    if (viewMode.value === "featured") return otherList.value;
    return entries.value.filter((e) => !e.featured);
  });

  const showAllGrid = computed(
    () => viewMode.value === "all" || selectedTags.value.length > 0 || !featuredList.value.length,
  );

  const selectedEntry = computed(() => {
    if (!entries.value.length) return null;
    return (
      entries.value.find((e) => e.catalog_id === selectedCatalogId.value) ?? entries.value[0]
    );
  });

  watch(
    entries,
    (list) => {
      if (!list.length) {
        selectedCatalogId.value = "";
        return;
      }
      if (!list.some((e) => e.catalog_id === selectedCatalogId.value)) {
        const preferred = list.find((e) => e.featured) ?? list[0];
        selectedCatalogId.value = preferred.catalog_id;
      }
    },
    { immediate: true },
  );

  function syncTagsToRoute() {
    const q = { ...route.query };
    if (selectedTags.value.length) {
      q.tags = selectedTags.value.join(",");
    } else {
      delete q.tags;
    }
    delete q.pick;
    router.replace({ query: q });
  }

  async function loadCatalog() {
    entries.value = await fetchCatalog({
      tags: selectedTags.value.length ? selectedTags.value : undefined,
    });
    const pick = String(route.query.pick ?? "");
    if (pick && entries.value.some((e) => e.catalog_id === pick)) {
      selectedCatalogId.value = pick;
    }
  }

  function toggleTag(tag: string) {
    const idx = selectedTags.value.indexOf(tag);
    if (idx >= 0) selectedTags.value.splice(idx, 1);
    else selectedTags.value.push(tag);
    tagQuery.value = selectedTags.value.join(", ");
    syncTagsToRoute();
    void loadCatalog().catch((e) => {
      error.value = formatApiError(e);
    });
  }

  function clearTagFilter() {
    selectedTags.value = [];
    tagQuery.value = "";
    syncTagsToRoute();
    void loadCatalog().catch((e) => {
      error.value = formatApiError(e);
    });
  }

  async function applyTagQuery() {
    selectedTags.value = parseCatalogTags(tagQuery.value);
    syncTagsToRoute();
    await loadCatalog();
  }

  function selectVoice(catalogId: string) {
    selectedCatalogId.value = catalogId;
    router.replace({ query: { ...route.query, pick: catalogId } });
  }

  function contactCreator(ownerUserId: string, voiceTitle?: string) {
    const draft = voiceTitle ? `你好，我对「${voiceTitle}」感兴趣，想咨询授权。` : "";
    router.push({
      path: "/community",
      query: { peer: ownerUserId, ...(draft ? { draft } : {}) },
    });
  }

  function goLibrary(versionId: string) {
    router.push({ path: "/library", query: { version: versionId } });
  }

  async function initFromRoute() {
    const fromQuery = parseCatalogTags(String(route.query.tags ?? ""));
    if (fromQuery.length) {
      selectedTags.value = fromQuery;
      tagQuery.value = fromQuery.join(", ");
    }
    try {
      availableTags.value = await fetchCatalogTags();
    } catch {
      availableTags.value = [];
    }
  }

  function clearAlerts() {
    error.value = "";
    success.value = "";
  }

  return {
    route,
    router,
    entries,
    availableTags,
    selectedTags,
    tagQuery,
    selectedCatalogId,
    viewMode,
    loading,
    error,
    success,
    featuredList,
    otherList,
    heroEntries,
    gridEntries,
    showAllGrid,
    selectedEntry,
    loadCatalog,
    toggleTag,
    clearTagFilter,
    applyTagQuery,
    selectVoice,
    contactCreator,
    goLibrary,
    initFromRoute,
    clearAlerts,
  };
}

export type CatalogBrowse = ReturnType<typeof useCatalogBrowse>;

export function useCatalogVoicesForEntry(selectedEntry: Ref<CatalogEntry | null>) {
  return computed(() => {
    const e = selectedEntry.value;
    if (!e) return [];
    return [{ id: e.voice_version_id, title: e.title, subtitle: e.voice_name }];
  });
}
