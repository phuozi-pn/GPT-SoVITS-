<script setup lang="ts">
import { formatPriceCents, getDevUserId, type CatalogEntry } from "@/api/catalog";
import TapePlayer from "@/modules/voice/components/studio/TapePlayer.vue";
import { avatarInitial, catalogAccessPillClass, catalogAccessStatus, licenseLabel } from "@/utils/catalogDisplay";

defineProps<{
  entries: CatalogEntry[];
  heroEntries: CatalogEntry[];
  gridEntries: CatalogEntry[];
  showAllGrid: boolean;
  selectedTags: string[];
  selectedCatalogId: string;
  availableTags: string[];
  tagQuery: string;
  loading: boolean;
}>();

const emit = defineEmits<{
  "update:tagQuery": [value: string];
  applyTagQuery: [];
  clearTagFilter: [];
  toggleTag: [tag: string];
  selectVoice: [catalogId: string];
  loadCatalog: [];
  contactCreator: [ownerUserId: string, voiceTitle?: string];
}>();

function accessOf(e: CatalogEntry) {
  return catalogAccessStatus(e, getDevUserId());
}
</script>

<template>
  <div class="catalog-toolbar">
    <div class="filter-bar catalog-toolbar__search">
      <input
        :value="tagQuery"
        placeholder="按标签筛选，如：短剧, 男声"
        @input="emit('update:tagQuery', ($event.target as HTMLInputElement).value)"
        @keyup.enter="emit('applyTagQuery')"
      />
      <button class="btn btn--primary btn--sm" :disabled="loading" @click="emit('applyTagQuery')">搜索</button>
      <button
        v-if="selectedTags.length"
        class="text-action"
        :disabled="loading"
        @click="emit('clearTagFilter')"
      >
        清除
      </button>
    </div>
    <div v-if="availableTags.length" class="tag-chips catalog-toolbar__tags">
      <button
        v-for="t in availableTags"
        :key="t"
        type="button"
        class="tag-chip"
        :class="{ 'tag-chip--active': selectedTags.includes(t) }"
        @click="emit('toggleTag', t)"
      >
        {{ t }}
      </button>
    </div>
  </div>

  <div v-if="heroEntries.length" class="catalog-hero-grid">
    <article
      v-for="e in heroEntries"
      :key="e.catalog_id"
      class="catalog-hero-card"
      :class="{ 'catalog-hero-card--on': selectedCatalogId === e.catalog_id }"
      role="button"
      tabindex="0"
      @click="emit('selectVoice', e.catalog_id)"
      @keydown.enter="emit('selectVoice', e.catalog_id)"
    >
      <div class="catalog-hero-card__head">
        <div class="catalog-hero-card__avatar" aria-hidden="true">{{ avatarInitial(e.title) }}</div>
        <div class="catalog-hero-card__meta">
          <span v-if="e.featured" class="catalog-hero-card__badge">平台精选</span>
          <h2 class="catalog-hero-card__title">{{ e.title }}</h2>
          <p class="catalog-hero-card__desc">{{ e.description || e.voice_name }}</p>
          <div class="meta-row catalog-hero-card__meta-row">
            <span>{{ e.voice_name }}</span>
            <span class="meta-row__sep">·</span>
            <span>{{ licenseLabel(e.license_type) }}</span>
            <span v-if="e.price_cents > 0" class="meta-row__sep">·</span>
            <span v-if="e.price_cents > 0">{{ e.included_chars.toLocaleString() }} 字额度</span>
          </div>
        </div>
        <div class="catalog-hero-card__price">
          <strong>{{ formatPriceCents(e.price_cents) }}</strong>
          <span v-if="e.price_cents > 0" class="hint">{{ e.included_chars.toLocaleString() }} 字</span>
          <span v-else class="hint">免费试听</span>
        </div>
      </div>

      <div v-if="e.tags.length" class="tag-line catalog-hero-card__tags">
        <span v-for="t in e.tags" :key="t" class="tag-line__item">{{ t }}</span>
      </div>

      <div v-if="e.demo_audio_url" class="catalog-hero-card__player" @click.stop>
        <TapePlayer :src="e.demo_audio_url" :height="88" />
      </div>
      <p v-else-if="e.demo_job_id" class="hint catalog-hero-card__nodemo">
        样音生成中…
        <button type="button" class="text-action" @click.stop="emit('loadCatalog')">刷新</button>
      </p>
      <p v-else class="hint catalog-hero-card__nodemo">暂无样音</p>

      <div class="catalog-hero-card__foot">
        <span class="hint">{{ licenseLabel(e.license_type) }}</span>
        <span :class="catalogAccessPillClass(accessOf(e).tone)">{{ accessOf(e).label }}</span>
        <div class="catalog-hero-card__actions row-actions">
          <button type="button" class="text-action text-action--accent" @click.stop="emit('selectVoice', e.catalog_id)">
            试听合成
          </button>
          <template v-if="e.owner_user_id !== getDevUserId()">
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <button
              type="button"
              class="text-action"
              @click.stop="emit('contactCreator', e.owner_user_id, e.title)"
            >
              联系创作者
            </button>
          </template>
          <span class="row-actions__sep" aria-hidden="true">·</span>
          <router-link class="text-action" :to="`/creator/${e.owner_user_id}`" @click.stop>主页</router-link>
        </div>
      </div>
    </article>
  </div>

  <div v-if="showAllGrid && gridEntries.length" class="catalog-more">
    <h3 class="catalog-more__title">
      {{ selectedTags.length ? "更多匹配" : "更多公开音色" }}
      <span class="hint">（{{ gridEntries.length }}）</span>
    </h3>
    <ul class="catalog-grid catalog-grid--compact">
      <li v-for="e in gridEntries" :key="e.catalog_id">
        <article
          class="voice-tile voice-tile--compact"
          :class="{ 'voice-tile--selected': selectedCatalogId === e.catalog_id }"
          role="button"
          tabindex="0"
          @click="emit('selectVoice', e.catalog_id)"
          @keydown.enter="emit('selectVoice', e.catalog_id)"
        >
          <div class="voice-tile__top">
            <div class="voice-tile__avatar" aria-hidden="true">{{ avatarInitial(e.title) }}</div>
            <div class="voice-tile__meta">
              <h3 class="voice-tile__title">{{ e.title }}</h3>
              <p class="hint voice-tile__price">
                {{ formatPriceCents(e.price_cents) }}
                <span v-if="!e.can_use && e.price_cents > 0" class="pill pill--warn">需购买</span>
              </p>
            </div>
          </div>
          <div v-if="e.demo_audio_url" class="voice-tile__audio" @click.stop>
            <TapePlayer :src="e.demo_audio_url" :height="52" />
          </div>
        </article>
      </li>
    </ul>
  </div>

  <div v-if="!entries.length" class="empty-state">
    <div class="empty-state__icon" aria-hidden="true">🎙</div>
    <p>
      {{
        selectedTags.length
          ? "没有符合这些标签的公开音色"
          : "还没有公开音色——创作者发布并审核通过后会出现在这里"
      }}
    </p>
  </div>
</template>
