<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchCatalog, fetchCatalogTags, formatPriceCents, type CatalogEntry } from "@/api/catalog";
import { apiJson } from "@/api/client";
import CatalogHeroCard from "@/components/CatalogHeroCard.vue";
import PublicPageHead from "@/modules/public/components/PublicPageHead.vue";
import ShareLink from "@/modules/public/components/ShareLink.vue";
import { formatApiError } from "@/utils/apiErrors";
import { catalogAppPath, catalogPurchasePath, loginToCatalogQuery } from "@/utils/catalogLinks";
import { hasAppSession } from "@/utils/session";

const route = useRoute();
const router = useRouter();
const loggedIn = computed(() => hasAppSession());

const entries = ref<CatalogEntry[]>([]);
const featuredEntries = ref<CatalogEntry[]>([]);
const availableTags = ref<string[]>([]);
const selectedTags = ref<string[]>([]);
const tagQuery = ref("");
const loading = ref(false);
const error = ref("");
const selectedId = ref("");
const showFeatured = ref(true);
const catalogStats = ref({ total_voices: 0, featured_voices: 0, tags_count: 0 });

const displayEntries = computed(() => {
  if (selectedTags.value.length || !showFeatured.value || !featuredEntries.value.length) {
    return entries.value;
  }
  const featuredIds = new Set(featuredEntries.value.map((e) => e.catalog_id));
  const rest = entries.value.filter((e) => !featuredIds.has(e.catalog_id));
  return [...featuredEntries.value, ...rest];
});

function goLogin(forAction: string, catalogId?: string) {
  const id = catalogId || selectedId.value || undefined;
  router.push({ path: "/login", query: loginToCatalogQuery(id, forAction) });
}

function goAppCatalog() {
  router.push(catalogAppPath(selectedId.value || undefined));
}

function goPurchase(catalogId?: string) {
  const id = catalogId || selectedId.value;
  if (!id) return;
  router.push(catalogPurchasePath(id));
}

function selectVoice(id: string) {
  selectedId.value = id;
  router.replace({ query: { ...route.query, pick: id } });
}


async function loadCatalogStats() {
  try {
    catalogStats.value = await apiJson<{ total_voices: number; featured_voices: number; tags_count: number }>(
      "/api/v1/public/catalog/stats",
    );
  } catch {
    // stats are optional
  }
}

async function loadFeatured() {
  try {
    featuredEntries.value = await fetchCatalog({ featured: true });
  } catch {
    featuredEntries.value = [];
  }
}

async function loadCatalog() {
  loading.value = true;
  error.value = "";
  try {
    entries.value = await fetchCatalog({
      tags: selectedTags.value.length ? selectedTags.value : undefined,
    });
    if (!selectedId.value && entries.value.length) {
      const pick = String(route.query.pick ?? "");
      selectedId.value = entries.value.some((e) => e.catalog_id === pick)
        ? pick
        : entries.value[0].catalog_id;
    }
  } catch (e) {
    error.value = formatApiError(e);
    entries.value = [];
  } finally {
    loading.value = false;
  }
}

function applyTagQuery() {
  selectedTags.value = tagQuery.value
    .split(/[,，]/)
    .map((t) => t.trim())
    .filter(Boolean)
    .slice(0, 10);
  showFeatured.value = false;
  void loadCatalog();
}

onMounted(async () => {
  try {
    availableTags.value = await fetchCatalogTags();
  } catch {
    availableTags.value = [];
  }
  await Promise.all([loadCatalog(), loadFeatured(), loadCatalogStats()]);
});

watch(
  () => route.query.pick,
  (pick) => {
    if (typeof pick === "string" && entries.value.some((e) => e.catalog_id === pick)) {
      selectedId.value = pick;
    }
  },
);
</script>

<template>
  <div class="showcase-browse">
    <PublicPageHead
      title="公开音色馆"
      hint="精选授权音色，先试听样音；满意后登录购买，即可在工作台合成出片"
    >
      <template #actions>
        <ShareLink label="分享本页" />
      </template>
    </PublicPageHead>

    <div v-if="loggedIn" class="showcase-browse__banner">
      <p class="hint">你已登录，可在工作台完成购买与合成</p>
      <button type="button" class="text-action text-action--accent" @click="goAppCatalog">进入完整音色馆 →</button>
    </div>

    <!-- Stats bar -->
    <div v-if="catalogStats.total_voices" class="showcase-browse__stats">
      <span class="showcase-browse__stat">
        <strong>{{ catalogStats.total_voices }}</strong> 个公开音色
      </span>
      <span class="showcase-browse__stat">
        <strong>{{ catalogStats.featured_voices }}</strong> 个精选推荐
      </span>
      <span class="showcase-browse__stat">
        <strong>{{ catalogStats.tags_count }}</strong> 个标签分类
      </span>
    </div>

    <div v-if="error" class="alert alert--error">{{ error }}</div>

    <div class="showcase-browse__toolbar">
      <input
        v-model="tagQuery"
        placeholder="按标签筛选，如：短剧, 男声"
        @keyup.enter="applyTagQuery"
      />
      <button type="button" class="btn btn--primary btn--sm" :disabled="loading" @click="applyTagQuery">搜索</button>
    </div>

    <div v-if="availableTags.length" class="tag-chips" style="margin-bottom: 16px">
      <button
        v-for="t in availableTags.slice(0, 12)"
        :key="t"
        type="button"
        class="tag-chip"
        :class="{ 'tag-chip--active': selectedTags.includes(t) }"
        @click="
          selectedTags = selectedTags.includes(t)
            ? selectedTags.filter((x) => x !== t)
            : [...selectedTags, t];
          showFeatured = false;
          void loadCatalog();
        "
      >
        {{ t }}
      </button>
    </div>

    <p v-if="loading" class="hint">加载中…</p>

    <div v-else-if="displayEntries.length" class="catalog-hero-grid showcase-browse__catalog">
      <CatalogHeroCard
        v-for="e in displayEntries"
        :key="e.catalog_id"
        :entry="e"
        :selected="selectedId === e.catalog_id"
        :show-access-pill="loggedIn"
        :show-contact="loggedIn"
        @select="selectVoice"
        @load-catalog="loadCatalog"
      >
        <template #actions="{ entry: item }">
          <template v-if="loggedIn">
            <button
              v-if="item.price_cents > 0 && !item.can_use"
              type="button"
              class="btn btn--primary btn--sm"
              @click.stop="goPurchase(item.catalog_id)"
            >
              购买授权 {{ formatPriceCents(item.price_cents) }}
            </button>
            <button
              type="button"
              class="btn btn--primary btn--sm"
              @click.stop="router.push(catalogAppPath(item.catalog_id))"
            >
              {{ item.can_use || item.price_cents === 0 ? "试听合成" : "进入工作台" }}
            </button>
          </template>
          <template v-else>
            <button
              type="button"
              class="btn btn--primary btn--sm"
              @click.stop="goLogin('purchase', item.catalog_id)"
            >
              {{ item.price_cents > 0 ? `购买授权 ${formatPriceCents(item.price_cents)}` : "登录免费使用" }}
            </button>
            <button type="button" class="text-action" @click.stop="goLogin('synth', item.catalog_id)">
              登录后合成
            </button>
          </template>
          <span class="row-actions__sep" aria-hidden="true">·</span>
          <router-link class="text-action" :to="`/creator/${item.owner_user_id}`" @click.stop>主页</router-link>
        </template>
      </CatalogHeroCard>
    </div>

    <div v-else class="empty-state">
      <p><strong>还没有公开音色</strong></p>
      <p class="hint">登录工作台后可训练并上架到音色馆</p>
    </div>
  </div>
</template>




