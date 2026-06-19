<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchCatalog, fetchCatalogTags, formatPriceCents, type CatalogEntry } from "@/api/catalog";
import { apiJson } from "@/api/client";
import TapePlayer from "@/modules/voice/components/studio/TapePlayer.vue";
import PublicPageHead from "@/modules/public/components/PublicPageHead.vue";
import ShareLink from "@/modules/public/components/ShareLink.vue";
import { formatApiError } from "@/utils/apiErrors";
import { catalogAppPath, catalogPurchasePath, loginToCatalogQuery } from "@/utils/catalogLinks";
import { licenseLabel } from "@/utils/catalogDisplay";
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

const selected = computed(() => entries.value.find((e) => e.catalog_id === selectedId.value));

function avatarInitial(title: string) {
  return title.trim().charAt(0) || "音";
}

function goLogin(forAction: string) {
  router.push({ path: "/login", query: loginToCatalogQuery(selectedId.value || undefined, forAction) });
}

function goAppCatalog() {
  router.push(catalogAppPath(selectedId.value || undefined));
}

function goPurchase() {
  if (!selectedId.value) return;
  router.push(catalogPurchasePath(selectedId.value));
}

function selectVoice(id: string) {
  selectedId.value = id;
  router.replace({ query: { ...route.query, pick: id } });
}

function goCreator(userId: string) {
  router.push(`/creator/${userId}`);
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
      hint="无需登录即可试听样音；购买授权、在线合成请登录工作台"
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

    <!-- Featured section -->
    <section v-if="showFeatured && featuredEntries.length" class="showcase-browse__featured">
      <h3 class="showcase-browse__section-title">精选推荐</h3>
      <div class="showcase-featured-grid">
        <button
          v-for="fe in featuredEntries.slice(0, 6)"
          :key="fe.catalog_id"
          type="button"
          class="showcase-featured-card"
          :class="{ 'showcase-featured-card--on': selectedId === fe.catalog_id }"
          @click="selectVoice(fe.catalog_id)"
        >
          <span class="showcase-featured-card__avatar" aria-hidden="true">{{ avatarInitial(fe.title) }}</span>
          <div class="showcase-featured-card__meta">
            <strong class="showcase-featured-card__title">{{ fe.title }}</strong>
            <span class="showcase-featured-card__price">{{ formatPriceCents(fe.price_cents) }}</span>
          </div>
          <span v-if="fe.tags.length" class="showcase-featured-card__tags">
            <span v-for="t in fe.tags.slice(0, 2)" :key="t" class="showcase-featured-card__tag">{{ t }}</span>
          </span>
        </button>
      </div>
    </section>

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

    <div v-else-if="entries.length" class="showcase-browse__layout showcase-browse__layout--film">
      <aside v-if="selected" class="showcase-browse__detail">
        <header class="showcase-browse__detail-head">
          <div>
            <h2 class="showcase-preview__title">{{ selected.title }}</h2>
            <p class="hint">{{ selected.description || selected.voice_name }}</p>
          </div>

          <div class="showcase-stamp" aria-label="授权与价格">
            <span class="showcase-stamp__label">{{ licenseLabel(selected.license_type) }}</span>
            <span class="showcase-stamp__price">{{ formatPriceCents(selected.price_cents) }}</span>
            <span v-if="!selected.can_use && selected.price_cents > 0" class="showcase-stamp__state showcase-stamp__state--warn">需购买</span>
            <span v-else-if="selected.can_use" class="showcase-stamp__state showcase-stamp__state--ok">已授权</span>
          </div>
        </header>

        <div v-if="selected.tags.length" class="tag-line" style="margin: 10px 0 12px">
          <span v-for="t in selected.tags" :key="t" class="tag-line__item">{{ t }}</span>
        </div>

        <TapePlayer v-if="selected.demo_audio_url" :src="selected.demo_audio_url" :height="104" />
        <p v-else class="hint">暂无样音</p>

        <div class="showcase-browse__detail-actions">
          <template v-if="loggedIn">
            <button
              v-if="selected.price_cents > 0 && !selected.can_use"
              type="button"
              class="btn btn--primary btn--sm"
              @click="goPurchase"
            >
              购买授权 {{ formatPriceCents(selected.price_cents) }}
            </button>
            <button
              type="button"
              class="btn btn--primary btn--sm"
              :class="{ 'btn--ghost': selected.price_cents > 0 && !selected.can_use }"
              @click="goAppCatalog"
            >
              {{ selected.can_use || selected.price_cents === 0 ? "试听合成" : "进入音色馆" }}
            </button>
          </template>
          <button v-else type="button" class="btn btn--primary btn--sm" @click="goLogin('purchase')">
            登录后购买 / 合成
          </button>
          <span class="row-actions" style="margin-left: 12px">
            <button type="button" class="text-action" @click="goCreator(selected.owner_user_id)">创作者</button>
          </span>
        </div>
      </aside>

      <ul class="showcase-filmstrip showcase-browse__filmstrip" aria-label="公开音色胶片带">
        <li v-for="e in entries" :key="e.catalog_id">
          <button
            type="button"
            class="showcase-voice-tile"
            :class="{ 'showcase-voice-tile--on': selectedId === e.catalog_id }"
            @click="selectVoice(e.catalog_id)"
          >
            <span class="showcase-voice-tile__avatar" aria-hidden="true">{{ avatarInitial(e.title) }}</span>
            <span class="showcase-voice-tile__meta">
              <strong>{{ e.title }}</strong>
              <span class="hint">{{ formatPriceCents(e.price_cents) }}</span>
            </span>
          </button>
        </li>
      </ul>
    </div>

    <div v-else class="empty-state">
      <p><strong>还没有公开音色</strong></p>
      <p class="hint">登录工作台后可训练并上架到音色馆</p>
    </div>
  </div>
</template>
