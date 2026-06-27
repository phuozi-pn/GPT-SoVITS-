<script setup lang="ts">
import { getDevUserId, type CatalogEntry } from "@/api/catalog";
import CatalogHeroCard from "@/components/CatalogHeroCard.vue";

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
  editEntry: [catalogId: string];
}>();
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
    <CatalogHeroCard
      v-for="e in heroEntries"
      :key="e.catalog_id"
      :entry="e"
      :selected="selectedCatalogId === e.catalog_id"
      @select="emit('selectVoice', $event)"
      @contact-creator="(id, title) => emit('contactCreator', id, title)"
      @load-catalog="emit('loadCatalog')"
    >
      <template v-if="e.owner_user_id === getDevUserId()" #actions>
        <button type="button" class="btn btn--primary btn--sm" @click.stop="emit('selectVoice', e.catalog_id)">
          试听合成
        </button>
        <button
          type="button"
          class="text-action text-action--accent"
          @click.stop="emit('editEntry', e.catalog_id)"
        >
          编辑发布
        </button>
      </template>
    </CatalogHeroCard>
  </div>

  <div v-if="showAllGrid && gridEntries.length" class="catalog-more">
    <h3 class="catalog-more__title">
      {{ selectedTags.length ? "更多匹配" : "更多公开音色" }}
      <span class="hint">（{{ gridEntries.length }}）</span>
    </h3>
    <div class="catalog-hero-grid catalog-hero-grid--stack">
      <CatalogHeroCard
        v-for="e in gridEntries"
        :key="e.catalog_id"
        :entry="e"
        :selected="selectedCatalogId === e.catalog_id"
        @select="emit('selectVoice', $event)"
        @contact-creator="(id, title) => emit('contactCreator', id, title)"
        @load-catalog="emit('loadCatalog')"
      >
        <template v-if="e.owner_user_id === getDevUserId()" #actions>
          <button type="button" class="btn btn--primary btn--sm" @click.stop="emit('selectVoice', e.catalog_id)">
            试听合成
          </button>
          <button
            type="button"
            class="text-action text-action--accent"
            @click.stop="emit('editEntry', e.catalog_id)"
          >
            编辑发布
          </button>
        </template>
      </CatalogHeroCard>
    </div>
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
