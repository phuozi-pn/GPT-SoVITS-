<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import CatalogAvatar from "@/components/CatalogAvatar.vue";
import type { CatalogEntry } from "@/api/catalog";
import { loadPlayableMediaUrl, revokePlayableMediaUrl } from "@/utils/authMedia";

const props = withDefaults(
  defineProps<{
    entry: Pick<CatalogEntry, "catalog_id" | "title" | "cover_image_url" | "tags">;
    src?: string | null;
    size?: "md" | "lg";
  }>(),
  { size: "lg" },
);

const audioRef = ref<HTMLAudioElement | null>(null);
const playing = ref(false);
const loading = ref(false);
const loadError = ref(false);
const playableSrc = ref("");

const canPlay = computed(() => Boolean(props.src) && Boolean(playableSrc.value) && !loadError.value);

async function refreshPlayableSrc() {
  loadError.value = false;
  playing.value = false;
  if (playableSrc.value && props.src) {
    revokePlayableMediaUrl(props.src);
  }
  playableSrc.value = "";
  if (!props.src) return;
  loading.value = true;
  try {
    playableSrc.value = await loadPlayableMediaUrl(props.src);
  } catch {
    loadError.value = true;
  } finally {
    loading.value = false;
  }
}

function onEnded() {
  playing.value = false;
}

function onPause() {
  playing.value = false;
}

function onPlay() {
  playing.value = true;
  loading.value = false;
}

function bindAudio() {
  const audio = audioRef.value;
  if (!audio) return;
  audio.onended = onEnded;
  audio.onpause = onPause;
  audio.onplay = onPlay;
  audio.onwaiting = () => {
    loading.value = true;
  };
  audio.oncanplay = () => {
    loading.value = false;
  };
}

async function toggle() {
  if (!canPlay.value) return;
  const audio = audioRef.value;
  if (!audio) return;
  if (!audio.paused) {
    audio.pause();
    return;
  }
  loading.value = true;
  try {
    await audio.play();
  } catch {
    loading.value = false;
    playing.value = false;
  }
}

watch(
  () => props.src,
  () => {
    void refreshPlayableSrc();
  },
  { immediate: true },
);

watch(playableSrc, () => {
  if (audioRef.value) {
    audioRef.value.pause();
    audioRef.value.load();
  }
  bindAudio();
});

onUnmounted(() => {
  audioRef.value?.pause();
  if (props.src) revokePlayableMediaUrl(props.src);
});
</script>

<template>
  <div class="voice-cover-play" :class="[`voice-cover-play--${size}`, { 'voice-cover-play--playing': playing }]">
    <CatalogAvatar :entry="entry" :size="size" />
    <button
      v-if="src"
      type="button"
      class="voice-cover-play__btn"
      :class="{ 'voice-cover-play__btn--busy': loading }"
      :disabled="!canPlay && !loading"
      :aria-label="playing ? '暂停试听' : '试听'"
      @click="toggle"
    >
      <svg v-if="playing && !loading" width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M7 6v12M17 6v12" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      </svg>
      <svg v-else-if="!loading" width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M8 6v12l10-6L8 6z" fill="currentColor" />
      </svg>
      <span v-else class="voice-cover-play__spinner" aria-hidden="true" />
    </button>
    <audio
      v-if="playableSrc"
      ref="audioRef"
      :src="playableSrc"
      preload="metadata"
      class="voice-cover-play__audio"
      @loadedmetadata="bindAudio"
    />
  </div>
</template>

<style scoped>
.voice-cover-play {
  position: relative;
  flex-shrink: 0;
}

.voice-cover-play__btn {
  position: absolute;
  right: -4px;
  bottom: -4px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 2px solid var(--bg-surface);
  border-radius: 999px;
  background: rgb(196 146 58 / 0.95);
  color: #0a0b0d;
  box-shadow: 0 2px 8px rgb(0 0 0 / 0.2);
  cursor: pointer;
  transition: transform 0.12s;
}

.voice-cover-play--md .voice-cover-play__btn {
  width: 24px;
  height: 24px;
}

.voice-cover-play__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.voice-cover-play__btn:not(:disabled):hover {
  transform: scale(1.06);
}

.voice-cover-play--playing .voice-cover-play__btn {
  background: var(--color-ink);
  color: #fff;
}

.voice-cover-play__spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgb(0 0 0 / 0.15);
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.voice-cover-play__audio {
  display: none;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
