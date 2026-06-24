<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import FeedComposeCard from "@/modules/social/components/FeedComposeCard.vue";
import FeedStreamList from "@/modules/social/components/FeedStreamList.vue";
import SocialSubNav from "@/modules/social/components/SocialSubNav.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import PageHero from "@/components/PageHero.vue";
import PageSurface from "@/components/PageSurface.vue";
import { useCommunityFeed } from "@/modules/social/composables/useCommunityFeed";

const route = useRoute();
const composeRef = ref<InstanceType<typeof FeedComposeCard> | null>(null);

const {
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
} = useCommunityFeed();

const activeFilterLabel = computed(
  () => filterTabs.value.find((t) => t.id === filter.value)?.label ?? "全部",
);

const itemCount = computed(() => displayedItems.value.length);

async function onPublished() {
  resetFilter();
  await loadFeed();
}

async function focusComposer() {
  await nextTick();
  await composeRef.value?.focus();
}

watch(
  () => route.query.compose,
  (v) => {
    if (v === "1") void focusComposer();
  },
  { immediate: true },
);

onMounted(() => {
  void loadFeed();
});
</script>

<template>
  <PageSurface class="page-surface--social">
    <PageHero compact flow title="发现">
      <template #stats>
        <p class="page-metrics">
          {{ activeFilterLabel }} · <strong>{{ loading ? "—" : itemCount }}</strong> 条
        </p>
      </template>
    </PageHero>

    <SocialSubNav />

    <div class="discover-feed discover-feed--split">
      <aside class="discover-feed__aside">
        <FeedComposeCard ref="composeRef" :loading="loading" @published="onPublished" @refresh="loadFeed" />

        <div class="discover-feed__filters">
          <p class="discover-feed__filters-label">筛选</p>
          <div class="feed-tabs feed-tabs--stack" role="tablist" aria-label="动态筛选">
            <button
              v-for="tab in filterTabs"
              :key="tab.id"
              type="button"
              role="tab"
              class="feed-tabs__item"
              :class="{ 'feed-tabs__item--on': filter === tab.id }"
              :aria-selected="filter === tab.id"
              @click="filter = tab.id"
            >
              {{ tab.label }}<span class="feed-tabs__count">{{ tab.count }}</span>
            </button>
          </div>
        </div>
      </aside>

      <main class="discover-feed__main">
        <div v-if="error" class="alert alert--error">{{ error }}</div>
        <LoadingSpinner v-if="loading" inline text="正在获取动态…" />

        <div v-else-if="feedEmpty" class="empty-state discover-feed__empty">
          <p><strong>{{ filter === "all" ? "暂无动态" : "暂无此类内容" }}</strong></p>
          <p class="hint">
            <template v-if="filter === 'all'">创作者上架后会出现「上新」；你也可以在左侧发布第一条动态。</template>
            <template v-else>切换其他筛选，或去音色馆浏览。</template>
          </p>
        </div>

        <FeedStreamList
          v-else
          gallery
          :items="displayedItems"
          mode="interactive"
          :loading-more="loadingMore"
          :next-before="nextBefore"
          @like="onLike"
          @catalog-pick="goCatalogPick"
          @creator="goCreator"
          @message="goMessage"
          @load-more="loadMore"
        />
      </main>
    </div>
  </PageSurface>
</template>

<style scoped>
.page-surface--social {
  flex: 1;
  min-height: 0;
  min-width: 0;
  width: 100%;
}
</style>
