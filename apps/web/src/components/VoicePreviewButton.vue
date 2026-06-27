<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import TransportButton from "@/modules/voice/components/studio/TransportButton.vue";
import { loadPlayableMediaUrl, revokePlayableMediaUrl } from "@/utils/authMedia";

const props = withDefaults(
  defineProps<{
    src?: string | null;
    size?: "md" | "lg";
    disabledHint?: string;
  }>(),
  { size: "lg", disabledHint: "暂无试听" },
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
  <div class="voice-preview-btn" :class="{ 'voice-preview-btn--disabled': !props.src || loadError }">
    <TransportButton
      :variant="playing ? 'pause' : 'play'"
      :size="size"
      :busy="loading"
      :disabled="!props.src || loadError || (!playableSrc && !loading)"
      :label="canPlay ? (playing ? '暂停' : '试听') : loadError ? '加载失败' : disabledHint"
      @click="toggle"
    />
    <audio
      v-if="playableSrc"
      ref="audioRef"
      :src="playableSrc"
      preload="metadata"
      class="voice-preview-btn__audio"
      @loadedmetadata="bindAudio"
    />
  </div>
</template>

<style scoped>
.voice-preview-btn {
  flex-shrink: 0;
}

.voice-preview-btn--disabled :deep(.transport-btn) {
  opacity: 0.45;
}

.voice-preview-btn__audio {
  display: none;
}
</style>
