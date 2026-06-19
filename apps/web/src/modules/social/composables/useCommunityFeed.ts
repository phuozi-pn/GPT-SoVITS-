import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { fetchCommunityFeed, togglePostLike, type FeedItem } from "@/api/community";
import { formatApiError } from "@/utils/apiErrors";

export type FeedFilter = "all" | "event" | "post";

export function useCommunityFeed() {
  const router = useRouter();

  const items = ref<FeedItem[]>([]);
  const loading = ref(false);
  const loadingMore = ref(false);
  const error = ref("");
  const nextBefore = ref<string | null>(null);
  const filter = ref<FeedFilter>("all");

  const eventCount = computed(() => items.value.filter((i) => i.type === "event").length);
  const postCount = computed(() => items.value.filter((i) => i.type === "post").length);

  const displayedItems = computed(() => {
    if (filter.value === "event") return items.value.filter((i) => i.type === "event");
    if (filter.value === "post") return items.value.filter((i) => i.type === "post");
    return items.value;
  });

  const feedEmpty = computed(() => !loading.value && displayedItems.value.length === 0);

  const filterTabs = computed(() => [
    { id: "all" as const, label: "全部", count: items.value.length },
    { id: "event" as const, label: "上新", count: eventCount.value },
    { id: "post" as const, label: "帖子", count: postCount.value },
  ]);

  async function loadFeed(limit = 30) {
    loading.value = true;
    error.value = "";
    try {
      const res = await fetchCommunityFeed({ limit });
      items.value = res.items;
      nextBefore.value = res.next_before;
    } catch (e) {
      error.value = formatApiError(e);
    } finally {
      loading.value = false;
    }
  }

  async function loadMore(limit = 30) {
    if (!nextBefore.value || loadingMore.value) return;
    loadingMore.value = true;
    error.value = "";
    try {
      const res = await fetchCommunityFeed({ before: nextBefore.value, limit });
      items.value = [...items.value, ...res.items];
      nextBefore.value = res.next_before;
    } catch (e) {
      error.value = formatApiError(e);
    } finally {
      loadingMore.value = false;
    }
  }

  async function onLike(postId: string) {
    try {
      const updated = await togglePostLike(postId);
      items.value = items.value.map((it) =>
        it.type === "post" && it.post.post_id === postId ? { ...it, post: updated } : it,
      );
    } catch (e) {
      error.value = formatApiError(e);
    }
  }

  function goCreator(userId: string) {
    router.push(`/creator/${userId}`);
  }

  function goCatalogPick(catalogId: string, appPath = "/catalog") {
    router.push({ path: appPath, query: { pick: catalogId } });
  }

  function goMessage(userId: string, voiceTitle?: string) {
    const query: Record<string, string> = { peer: userId };
    if (voiceTitle) {
      query.draft = `你好，想咨询「${voiceTitle}」的授权与合作。`;
    }
    router.push({ path: "/community", query });
  }

  function resetFilter() {
    filter.value = "all";
  }

  return {
    items,
    loading,
    loadingMore,
    error,
    nextBefore,
    filter,
    displayedItems,
    feedEmpty,
    filterTabs,
    loadFeed,
    loadMore,
    onLike,
    goCreator,
    goCatalogPick,
    goMessage,
    resetFilter,
  };
}
