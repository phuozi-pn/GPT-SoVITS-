<script setup lang="ts">
import { formatPriceCents, getDevUserId, type CatalogEntry } from "@/api/catalog";
import CatalogAvatar from "@/components/CatalogAvatar.vue";
import VoiceCatalogMeta from "@/components/VoiceCatalogMeta.vue";
import TapePlayer from "@/modules/voice/components/studio/TapePlayer.vue";
import {
  catalogAccessPillClass,
  catalogAccessStatus,
  catalogPublicDescription,
  licenseLabel,
} from "@/utils/catalogDisplay";

const props = withDefaults(
  defineProps<{
    entry: CatalogEntry;
    selected?: boolean;
    viewerUserId?: string;
    showFooter?: boolean;
    showContact?: boolean;
    showAccessPill?: boolean;
    selectOnClick?: boolean;
    tagLimit?: number;
  }>(),
  {
    selected: false,
    viewerUserId: undefined,
    showFooter: true,
    showContact: true,
    showAccessPill: true,
    selectOnClick: true,
    tagLimit: 8,
  },
);

const emit = defineEmits<{
  select: [catalogId: string];
  contactCreator: [ownerUserId: string, voiceTitle?: string];
  loadCatalog: [];
}>();

function viewerId() {
  return props.viewerUserId ?? getDevUserId();
}

function accessOf(e: CatalogEntry) {
  return catalogAccessStatus(e, viewerId());
}

function publicDesc(e: CatalogEntry) {
  return catalogPublicDescription(e);
}
</script>

<template>
  <article
    class="catalog-hero-card"
    :class="{ 'catalog-hero-card--on': selected }"
    :data-catalog-id="entry.catalog_id"
    role="button"
    tabindex="0"
    @click="selectOnClick && emit('select', entry.catalog_id)"
    @keydown.enter="selectOnClick && emit('select', entry.catalog_id)"
  >
    <div class="catalog-hero-card__head">
      <CatalogAvatar :entry="entry" size="lg" />
      <div class="catalog-hero-card__meta">
        <span v-if="entry.featured" class="catalog-hero-card__badge">平台精选</span>
        <h2 class="catalog-hero-card__title">{{ entry.title }}</h2>
        <VoiceCatalogMeta
          :entry="entry"
          prominent
          tags-only
          :show-scenes="false"
          :tag-limit="tagLimit"
        />
        <p v-if="publicDesc(entry)" class="catalog-hero-card__desc">{{ publicDesc(entry) }}</p>
        <VoiceCatalogMeta :entry="entry" prominent :show-tags="false" />
      </div>
      <div class="catalog-hero-card__price">
        <strong>{{ formatPriceCents(entry.price_cents) }}</strong>
        <span v-if="entry.price_cents > 0" class="catalog-hero-card__quota">
          {{ entry.included_chars.toLocaleString() }} 字授权
        </span>
        <span v-else class="hint">免费试听</span>
      </div>
    </div>

    <div v-if="entry.demo_audio_url" class="catalog-hero-card__player" @click.stop>
      <TapePlayer :src="entry.demo_audio_url" :height="88" />
    </div>
    <p v-else-if="entry.demo_job_id" class="hint catalog-hero-card__nodemo">
      样音生成中
      <button type="button" class="text-action" @click.stop="emit('loadCatalog')">刷新</button>
    </p>

    <div v-if="showFooter" class="catalog-hero-card__foot">
      <span class="catalog-hero-card__license">{{ licenseLabel(entry.license_type) }}</span>
      <span v-if="showAccessPill" :class="catalogAccessPillClass(accessOf(entry).tone)">
        {{ accessOf(entry).label }}
      </span>
      <div class="catalog-hero-card__actions row-actions">
        <slot name="actions" :entry="entry">
          <button
            type="button"
            class="btn btn--primary btn--sm"
            @click.stop="emit('select', entry.catalog_id)"
          >
            试听合成
          </button>
          <template v-if="showContact && entry.owner_user_id !== viewerId()">
            <button
              type="button"
              class="text-action"
              @click.stop="emit('contactCreator', entry.owner_user_id, entry.title)"
            >
              联系创作者
            </button>
          </template>
        </slot>
      </div>
    </div>
  </article>
</template>
