<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  fetchCreatorProfile,
  formatPriceCents,
  type CatalogEntry,
  type CreatorProfile,
} from "@/api/catalog";
import {
  catalogDemoDownloadUrl,
  catalogVoicePackUrl,
  downloadCatalogAsset,
  fetchUserProfile,
} from "@/api/social";
import UserAvatar from "@/components/UserAvatar.vue";
import TapePlayer from "@/modules/voice/components/studio/TapePlayer.vue";
import { formatApiError } from "@/utils/apiErrors";

const props = defineProps<{
  peerUserId: string;
  peerName: string;
}>();

const emit = defineEmits<{
  mentionVoice: [text: string];
}>();

const router = useRouter();
const profile = ref<CreatorProfile | null>(null);
const bio = ref("");
const loading = ref(false);
const error = ref("");
const downloadBusy = ref("");

async function load() {
  if (!props.peerUserId) return;
  loading.value = true;
  error.value = "";
  try {
    const [creator, pub] = await Promise.all([
      fetchCreatorProfile(props.peerUserId),
      fetchUserProfile(props.peerUserId),
    ]);
    profile.value = creator;
    bio.value = pub.bio || creator.bio;
  } catch (e) {
    error.value = formatApiError(e);
    profile.value = null;
  } finally {
    loading.value = false;
  }
}

function goCatalog(entry: CatalogEntry) {
  router.push({ path: "/catalog", query: { pick: entry.catalog_id } });
}

function mentionVoice(entry: CatalogEntry) {
  const price = formatPriceCents(entry.price_cents);
  emit(
    "mentionVoice",
    `你好，我对「${entry.title}」感兴趣（${price}），想了解一下授权和使用方式。`,
  );
}

async function onDownloadDemo(entry: CatalogEntry) {
  downloadBusy.value = entry.catalog_id;
  try {
    await downloadCatalogAsset(catalogDemoDownloadUrl(entry.catalog_id), `${entry.title}_demo.wav`);
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    downloadBusy.value = "";
  }
}

async function onDownloadPack(entry: CatalogEntry) {
  downloadBusy.value = `${entry.catalog_id}-pack`;
  try {
    await downloadCatalogAsset(catalogVoicePackUrl(entry.catalog_id), `${entry.title}_pack.zip`);
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    downloadBusy.value = "";
  }
}

onMounted(() => void load());
watch(() => props.peerUserId, () => void load());
</script>

<template>
  <aside class="peer-panel">
    <!-- Compact header row -->
    <div class="peer-panel__head">
      <UserAvatar :name="peerName" size="sm" />
      <div class="peer-panel__head-meta">
        <strong class="peer-panel__name">{{ peerName }}</strong>
        <p class="peer-panel__bio">{{ bio || "暂无简介" }}</p>
      </div>
      <div class="peer-panel__head-close">
        <slot name="actions" />
      </div>
    </div>

    <div v-if="error" class="alert alert--error peer-panel__alert">{{ error }}</div>

    <div v-if="loading" class="peer-panel__loading">加载中…</div>

    <template v-else-if="profile">
      <div class="peer-panel__section-title">
        <span class="rack-label">{{ profile.published_count }} 个音色</span>
      </div>

      <ul v-if="profile.voices.length" class="peer-panel__voices">
        <li v-for="v in profile.voices" :key="v.catalog_id" class="voice-card">
          <div class="voice-card__cover">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" opacity="0.6">
              <path d="M9 18V5l12-2v13" />
              <circle cx="6" cy="18" r="3" />
              <circle cx="18" cy="16" r="3" />
            </svg>
            <span class="voice-card__price-tag">{{ formatPriceCents(v.price_cents) }}</span>
          </div>

          <div class="voice-card__body">
            <strong class="voice-card__title">{{ v.title }}</strong>
            <p v-if="v.description" class="voice-card__desc">{{ v.description }}</p>

            <div v-if="v.demo_audio_url" class="voice-card__player" @click.stop>
              <TapePlayer :src="v.demo_audio_url" :height="28" />
            </div>
            <p v-else class="voice-card__nodemo">暂无样音</p>

            <div class="voice-card__actions row-actions">
              <button type="button" class="text-action text-action--accent" @click="mentionVoice(v)">咨询</button>
              <span class="row-actions__sep" aria-hidden="true">·</span>
              <button type="button" class="text-action" @click="goCatalog(v)">音色馆</button>
              <template v-if="v.demo_audio_url">
                <span class="row-actions__sep" aria-hidden="true">·</span>
                <button type="button" class="text-action" :disabled="!!downloadBusy" @click="onDownloadDemo(v)">下载样音</button>
              </template>
              <template v-if="v.can_use || v.price_cents === 0">
                <span class="row-actions__sep" aria-hidden="true">·</span>
                <button type="button" class="text-action" :disabled="!!downloadBusy" @click="onDownloadPack(v)">音色包</button>
              </template>
            </div>
          </div>
        </li>
      </ul>
      <p v-else class="peer-panel__empty">暂无公开音色</p>
    </template>
  </aside>
</template>

<style scoped>
/* ── Panel container ── */
.peer-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  border-left: 1px solid rgb(212 205 195 / 0.25);
  background: var(--bg-surface);
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: thin;
  scrollbar-color: rgb(212 205 195 / 0.3) transparent;
}

.peer-panel::-webkit-scrollbar {
  width: 5px;
}

.peer-panel::-webkit-scrollbar-track {
  background: transparent;
}

.peer-panel::-webkit-scrollbar-thumb {
  background: rgb(212 205 195 / 0.35);
  border-radius: 999px;
}

.peer-panel::-webkit-scrollbar-thumb:hover {
  background: rgb(212 205 195 / 0.55);
}

/* ── Header: ultra-compact row ── */
.peer-panel__head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-bottom: 1px solid rgb(212 205 195 / 0.2);
  background: var(--bg-surface);
}

.peer-panel__head-meta {
  flex: 1;
  min-width: 0;
}

.peer-panel__name {
  display: block;
  font-size: 12px;
  font-weight: 600;
  font-family: var(--font-display);
}

.peer-panel__bio {
  margin: 0;
  font-size: 10px;
  line-height: 1.2;
  color: var(--color-ink-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.peer-panel__head-close {
  flex-shrink: 0;
}

/* ── Alerts / loading ── */
.peer-panel__alert {
  margin: 4px 6px 0;
  font-size: 9px;
}

.peer-panel__loading {
  padding: 10px;
  text-align: center;
  font-size: 10px;
  color: var(--color-ink-muted);
}

.peer-panel__empty {
  padding: 10px;
  text-align: center;
  font-size: 10px;
  color: var(--color-ink-muted);
}

/* ── Section divider ── */
.peer-panel__section-title {
  padding: 8px 10px 4px;
}

.peer-panel__section-title .rack-label {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--color-ink-muted);
  text-transform: uppercase;
}

/* ── Voice list ── */
.peer-panel__voices {
  list-style: none;
  margin: 0;
  padding: 0 6px 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* ── Voice card: ultra-compact row ── */
.voice-card {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 8px;
  background: transparent;
  transition: background 0.15s ease;
}

.voice-card:hover {
  background: var(--bg-surface-muted);
}

/* Tiny cover */
.voice-card__cover {
  position: relative;
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: linear-gradient(135deg, var(--color-vu-amber-soft), rgb(212 146 74 / 0.08));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-vu-amber);
}

.voice-card__price-tag {
  position: absolute;
  bottom: -2px;
  left: 50%;
  transform: translateX(-50%);
  padding: 0 3px;
  border-radius: 999px;
  background: var(--bg-surface);
  border: 1px solid rgb(212 205 195 / 0.35);
  font-size: 7px;
  font-weight: 600;
  color: var(--color-ink-muted);
  white-space: nowrap;
  line-height: 1.3;
}

/* Body */
.voice-card__body {
  flex: 1;
  min-width: 0;
}

.voice-card__title {
  font-size: 11px;
  font-weight: 600;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.voice-card__desc {
  margin: 1px 0 0;
  font-size: 10px;
  line-height: 1.3;
  color: var(--color-ink-muted);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.voice-card__player {
  margin-top: 4px;
}

.voice-card__nodemo {
  margin: 2px 0 0;
  font-size: 9px;
  color: var(--color-ink-muted);
}

/* Actions: expand on hover via inline */
.voice-card__actions {
  display: none;
  margin-top: 4px;
}

.voice-card:hover .voice-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
