<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  fetchFeaturedCreators,
  fetchPublicCatalog,
  type FeaturedCreatorSummary,
} from "@/api/public";
import type { CatalogEntry } from "@/api/catalog";
import CatalogHeroCard from "@/components/CatalogHeroCard.vue";
import CatalogAvatar from "@/components/CatalogAvatar.vue";
import CreatorAvatar from "@/components/CreatorAvatar.vue";
import VoiceCatalogMeta from "@/components/VoiceCatalogMeta.vue";
import { formatPriceCents } from "@/api/catalog";
import { displayVoiceCastLine } from "@/utils/catalogDisplay";
import { formatApiError } from "@/utils/apiErrors";
import { catalogAppPath, catalogPurchasePath, loginToCatalogQuery } from "@/utils/catalogLinks";
import { hasAppSession } from "@/utils/session";

const router = useRouter();
const loggedIn = computed(() => hasAppSession());

const loading = ref(true);
const error = ref("");
const featuredVoices = ref<CatalogEntry[]>([]);
const creators = ref<FeaturedCreatorSummary[]>([]);
const activeVoiceId = ref("");
const activeCreatorId = ref("");
const creatorWorks = ref<CatalogEntry[]>([]);
const creatorWorksLoading = ref(false);

const activeVoice = computed(() =>
  featuredVoices.value.find((v) => v.catalog_id === activeVoiceId.value) ?? null,
);

const activeCreator = computed(() =>
  creators.value.find((c) => c.user_id === activeCreatorId.value) ?? null,
);

function selectVoice(id: string) {
  activeVoiceId.value = id;
}

async function loadCreatorWorks(userId: string) {
  creatorWorksLoading.value = true;
  try {
    creatorWorks.value = await fetchPublicCatalog({ owner: userId, page_size: 8 });
  } catch {
    creatorWorks.value = [];
  } finally {
    creatorWorksLoading.value = false;
  }
}

async function selectCreator(creator: FeaturedCreatorSummary) {
  activeCreatorId.value = creator.user_id;
  if (creator.spotlight_voice) {
    activeVoiceId.value = creator.spotlight_voice.catalog_id;
  }
  await loadCreatorWorks(creator.user_id);
}

function goCreator(userId: string) {
  router.push(`/creator/${userId}`);
}

function voicePillTag(voice: CatalogEntry) {
  return displayVoiceCastLine(voice.tags ?? []);
}

function goBrowse(pick?: string) {
  router.push(pick ? `/browse?pick=${pick}` : "/browse");
}

function goLoginPurchase(catalogId: string) {
  router.push({ path: "/login", query: loginToCatalogQuery(catalogId, "purchase") });
}

function goPurchase(catalogId: string) {
  router.push(catalogPurchasePath(catalogId));
}

function goSynth(catalogId: string) {
  router.push(catalogAppPath(catalogId));
}

function purchaseLabel(entry: CatalogEntry) {
  if (entry.price_cents > 0) return `购买授权 ${formatPriceCents(entry.price_cents)}`;
  return "免费注册使用";
}

onMounted(async () => {
  loading.value = true;
  error.value = "";
  try {
    const [voices, creatorList] = await Promise.all([
      fetchPublicCatalog({ featured: true, page_size: 12 }),
      fetchFeaturedCreators(8),
    ]);
    featuredVoices.value = voices;
    creators.value = creatorList;
    if (voices[0]) activeVoiceId.value = voices[0].catalog_id;
    if (creatorList[0]) await selectCreator(creatorList[0]);
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <section class="home-showcase" aria-label="优质音色与明星创作者">
    <header class="home-showcase__header">
      <div class="home-showcase__header-copy">
        <p class="home-showcase__eyebrow">
          <span class="home-showcase__eyebrow-dot" aria-hidden="true" />
          CURATED VOICES
        </p>
        <h2 class="home__section-title home-showcase__title">优质音色 · 明星创作者</h2>
        <p class="home-showcase__lead">
          先试听样音，满意再购买授权；含商用额度，登录后即可合成出片。
        </p>
      </div>
      <router-link to="/browse" class="home-showcase__browse-link text-action">进入音色馆 →</router-link>
    </header>

    <p v-if="loading" class="home-showcase__status">加载精选内容…</p>
    <p v-else-if="error" class="home-showcase__status home-showcase__status--error">{{ error }}</p>
    <p v-else-if="!featuredVoices.length && !creators.length" class="home-showcase__status">
      暂无精选内容，可前往 <router-link to="/browse">音色馆</router-link> 浏览
    </p>

    <div v-else class="home-showcase__stage">
      <div class="home-showcase__main">
        <div v-if="featuredVoices.length" class="home-showcase__voice-rail" role="list" aria-label="精选音色列表">
          <button
            v-for="voice in featuredVoices"
            :key="voice.catalog_id"
            type="button"
            class="home-showcase__voice-pill"
            :class="{ 'home-showcase__voice-pill--on': activeVoiceId === voice.catalog_id }"
            @click="selectVoice(voice.catalog_id)"
          >
            <span class="home-showcase__pill-avatar" aria-hidden="true">
              <CatalogAvatar :entry="voice" size="sm" />
            </span>
            <span class="home-showcase__pill-body">
              <strong>{{ voice.title }}</strong>
              <span v-if="voicePillTag(voice)" class="home-showcase__pill-tag">{{ voicePillTag(voice) }}</span>
            </span>
          </button>
        </div>

        <CatalogHeroCard
          v-if="activeVoice"
          :entry="activeVoice"
          selected
          :select-on-click="false"
          :show-access-pill="false"
          :show-contact="false"
          @select="goBrowse"
        >
          <template #actions="{ entry }">
            <button
              v-if="!loggedIn"
              type="button"
              class="btn btn--primary btn--sm"
              @click.stop="goLoginPurchase(entry.catalog_id)"
            >
              {{ purchaseLabel(entry) }}
            </button>
            <button
              v-else-if="entry.price_cents > 0 && !entry.can_use"
              type="button"
              class="btn btn--primary btn--sm"
              @click.stop="goPurchase(entry.catalog_id)"
            >
              {{ purchaseLabel(entry) }}
            </button>
            <button
              v-else
              type="button"
              class="btn btn--primary btn--sm"
              @click.stop="goSynth(entry.catalog_id)"
            >
              试听合成
            </button>
            <button type="button" class="text-action" @click.stop="goBrowse(entry.catalog_id)">
              浏览更多
            </button>
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <button type="button" class="text-action" @click.stop="goCreator(entry.owner_user_id)">
              创作者主页
            </button>
          </template>
        </CatalogHeroCard>
      </div>

      <aside class="home-showcase__creators" aria-label="明星创作者">
        <div class="home-showcase__creators-head">
          <div>
            <h3 class="home-showcase__subhead">明星创作者</h3>
            <p class="home-showcase__creators-hint">认证精选作者，代表作一键试听</p>
          </div>
          <router-link to="/creators" class="text-action">全部创作者</router-link>
        </div>

        <div class="home-showcase__creator-list">
          <button
            v-for="creator in creators"
            :key="creator.user_id"
            type="button"
            class="home-showcase__creator-card"
            :class="{ 'home-showcase__creator-card--on': activeCreatorId === creator.user_id }"
            @click="selectCreator(creator)"
          >
            <span class="home-showcase__creator-ring" aria-hidden="true">
              <CreatorAvatar
                :display-name="creator.display_name"
                :avatar-url="creator.avatar_url"
                :user-id="creator.user_id"
                size="sm"
              />
            </span>
            <span class="home-showcase__creator-meta">
              <strong>{{ creator.display_name }}</strong>
              <span>{{ creator.published_count }} 作品 · {{ creator.featured_voice_count }} 精选</span>
              <span v-if="creator.bio" class="home-showcase__creator-bio">{{ creator.bio }}</span>
            </span>
            <span class="home-showcase__creator-chevron" aria-hidden="true">›</span>
          </button>
        </div>

        <div v-if="activeCreator" class="home-showcase__creator-foot">
          <p class="home-showcase__works-title">{{ activeCreator.display_name }} 的代表作</p>
          <p v-if="creatorWorksLoading" class="home-showcase__status">加载作品…</p>
          <ul v-else-if="creatorWorks.length" class="home-showcase__works-list">
            <li v-for="work in creatorWorks" :key="work.catalog_id">
              <button type="button" class="home-showcase__work-item" @click="selectVoice(work.catalog_id)">
                <div class="home-showcase__work-head">
                  <strong>{{ work.title }}</strong>
                  <span class="home-showcase__work-price">{{ formatPriceCents(work.price_cents) }}</span>
                </div>
                <VoiceCatalogMeta :entry="work" :tag-limit="4" tags-only prominent :show-scenes="false" />
              </button>
            </li>
          </ul>
          <p v-else class="home-showcase__status">暂无公开作品</p>
          <button type="button" class="home__btn home__btn--ghost home__btn--sm" @click="goCreator(activeCreator.user_id)">
            查看全部作品
          </button>
        </div>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.home-showcase {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.home-showcase__header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px 20px;
}

.home-showcase__eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.14em;
  color: var(--color-brushed-dark);
}

.home-showcase__eyebrow-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: var(--color-vu-amber);
}

.home-showcase__title {
  margin-bottom: 8px;
}

.home-showcase__lead,
.home-showcase__creators-hint,
.home-showcase__status {
  margin: 0;
  font-size: 14px;
  line-height: 1.65;
  color: var(--color-ink-muted);
}

.home-showcase__browse-link {
  flex-shrink: 0;
  font-size: 14px;
}

.home-showcase__status--error {
  color: var(--color-peak-red);
}

/* 左：精选大卡；右：创作者侧栏 */
.home-showcase__stage {
  display: grid;
  gap: 20px;
}

@media (min-width: 1024px) {
  .home-showcase__stage {
    grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.65fr);
    align-items: start;
  }
}

.home-showcase__main {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.home-showcase__creators {
  padding: 18px 20px 20px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-module);
  background: var(--bg-surface-muted);
  box-shadow: var(--shadow-card);
}

.home-showcase__subhead {
  margin: 0;
  font-family: var(--font-scroll);
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.home-showcase__creators-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.home-showcase__voice-rail {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
  margin-bottom: 16px;
  scrollbar-width: thin;
}

.home-showcase__voice-pill {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  min-width: 160px;
  max-width: 210px;
  padding: 9px 11px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-ui);
  background: var(--bg-surface-muted);
  text-align: left;
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out);
}

.home-showcase__voice-pill:hover {
  border-color: var(--color-line-strong);
  background: var(--color-indigo-soft);
}

.home-showcase__voice-pill--on {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
}

.home-showcase__pill-avatar {
  display: flex;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
}

.home-showcase__pill-avatar :deep(.catalog-avatar) {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-ui);
  box-shadow: none;
}

.home-showcase__pill-avatar :deep(.catalog-avatar__fallback) {
  font-size: 15px;
}

.home-showcase__pill-body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.home-showcase__pill-body strong {
  font-size: 13px;
  color: var(--color-ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.home-showcase__pill-tag {
  font-size: 11px;
  color: var(--color-vu-amber-deep);
}

.home-showcase__creator-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.home-showcase__creator-card {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 11px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-ui);
  background: var(--color-surface);
  text-align: left;
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out);
}

.home-showcase__creator-card:hover {
  border-color: var(--color-line-strong);
  background: var(--color-indigo-soft);
}

.home-showcase__creator-card--on {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
}

.home-showcase__creator-ring {
  display: flex;
  padding: 2px;
  border-radius: 999px;
  background: linear-gradient(145deg, var(--theme-warm) 0%, var(--color-vu-amber-deep) 100%);
}

.home-showcase__creator-ring :deep(.creator-avatar) {
  box-shadow: none;
}

.home-showcase__creator-meta {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
  font-size: 12px;
  color: var(--color-ink-muted);
}

.home-showcase__creator-meta strong {
  font-size: 14px;
  color: var(--color-ink);
}

.home-showcase__creator-bio {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.home-showcase__creator-chevron {
  font-size: 20px;
  line-height: 1;
  color: var(--color-brushed-dark);
}

.home-showcase__creator-foot {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--color-line);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.home-showcase__works-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-ink);
}

.home-showcase__works-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.home-showcase__work-item {
  display: flex;
  width: 100%;
  flex-direction: column;
  gap: 6px;
  padding: 9px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-ui);
  background: var(--color-surface);
  text-align: left;
  cursor: pointer;
}

.home-showcase__work-item:hover {
  border-color: var(--color-line-strong);
  background: var(--color-indigo-soft);
}

.home-showcase__work-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.home-showcase__work-head strong {
  font-size: 13px;
  color: var(--color-ink);
}

.home-showcase__work-price {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--color-vu-amber-deep);
}

.home__btn--sm {
  padding: 8px 14px;
  font-size: 13px;
}
</style>
