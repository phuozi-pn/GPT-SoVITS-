<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import FeedStreamList from "@/modules/social/components/FeedStreamList.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import ShareLink from "@/modules/public/components/ShareLink.vue";
import { useCommunityFeed } from "@/modules/social/composables/useCommunityFeed";
import { getPageMeta } from "@/config/navigation";
import { hasAppSession } from "@/utils/session";

const router = useRouter();
const route = useRoute();
const loggedIn = computed(() => hasAppSession());
const pageMeta = computed(() => getPageMeta(route.path, String(route.name ?? "")));

const {
  items,
  loading,
  loadingMore,
  error,
  nextBefore,
  feedEmpty,
  loadFeed,
  loadMore,
  goCatalogPick,
} = useCommunityFeed();

function goCatalogPublic(catalogId: string) {
  goCatalogPick(catalogId, hasAppSession() ? "/catalog" : "/browse");
}

function goLogin() {
  router.push({ path: "/login", query: { redirect: "/discover/feed" } });
}

function goAppDiscover() {
  router.push("/discover/feed");
}

onMounted(() => {
  void loadFeed(20);
});
</script>

<template>
  <div class="social-page">
    <header class="social-page__head">
      <h1 class="social-page__title">{{ pageMeta.label }}</h1>
      <p class="social-page__lead">{{ pageMeta.desc }}</p>
    </header>

    <div class="social-toolbar" style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center">
      <button v-if="loggedIn" type="button" class="btn-formal" @click="goAppDiscover">进入完整社区</button>
      <button v-else type="button" class="btn-formal btn-formal--primary" @click="goLogin">登录</button>
      <ShareLink label="分享" />
      <button type="button" class="text-action" :disabled="loading" @click="loadFeed(20)">刷新</button>
    </div>

    <div v-if="error" class="alert alert--error">{{ error }}</div>
    <LoadingSpinner v-if="loading" inline text="正在获取动态…" />

    <div v-else-if="feedEmpty" class="empty-state">
      <p><strong>还没有公开动态</strong></p>
      <p class="hint" style="margin-top: 8px">创作者上架音色后会出现「上新」</p>
    </div>

    <FeedStreamList
      v-else
      gallery
      :items="items"
      mode="readonly"
      :loading-more="loadingMore"
      :next-before="nextBefore"
      @catalog-pick="goCatalogPublic"
      @load-more="() => loadMore(20)"
    />
  </div>
</template>
