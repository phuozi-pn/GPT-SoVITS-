<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { resolveMediaUrl } from "@/config";
import { readTimeDomain, useAudioAnalyser } from "@/composables/useAudioAnalyser";
import { useCanvasWaveform } from "@/composables/useCanvasWaveform";
import {
  fetchAudioPeaks,
  idleScopePoints,
  peaksToScopePoints,
  timeDomainToScopePoints,
} from "@/utils/audioWaveform";
import { drawPaperGrid, drawScopeCurve } from "@/utils/oscilloscope";
import TapeReel from "@/modules/voice/components/studio/TapeReel.vue";
import TransportButton from "@/modules/voice/components/studio/TransportButton.vue";

const props = withDefaults(
  defineProps<{ src: string; height?: number }>(),
  { height: 88 },
);

const mediaSrc = computed(() => resolveMediaUrl(props.src));

const canvasRef = ref<HTMLCanvasElement | null>(null);
const audioRef = ref<HTMLAudioElement | null>(null);
const { resize, observeResize } = useCanvasWaveform(canvasRef);
const { isPlaying, bindPlaybackHandlers } = useAudioAnalyser(audioRef);

const currentTime = ref(0);
const duration = ref(0);
const isDragging = ref(false);
const peaks = ref<Float32Array | null>(null);
const peaksError = ref(false);
let raf = 0;
let loadToken = 0;

const progress = computed(() => (duration.value ? currentTime.value / duration.value : 0));

async function loadPeaks(width: number) {
  const token = ++loadToken;
  peaksError.value = false;
  try {
    const count = Math.max(120, Math.floor(width / 2));
    const data = await fetchAudioPeaks(mediaSrc.value, count);
    if (token === loadToken) peaks.value = data;
  } catch {
    if (token === loadToken) {
      peaks.value = null;
      peaksError.value = true;
    }
  }
}

function paint(w: number, h: number) {
  const ctx = canvasRef.value?.getContext("2d");
  if (!ctx || w <= 0) return;
  drawPaperGrid(ctx, w, h);

  let points: { x: number; y: number }[] = [];
  let curveProgress = 1;

  if (isPlaying.value && audioRef.value) {
    const td = readTimeDomain(audioRef.value);
    if (td) {
      points = timeDomainToScopePoints(w, h, td);
    }
  }

  if (!points.length && peaks.value) {
    points = peaksToScopePoints(w, h, peaks.value, 1);
    curveProgress = progress.value;
  }

  if (!points.length) {
    points = idleScopePoints(w, h);
  }

  const color = peaksError.value ? "rgba(199, 93, 77, 0.85)" : "#E8A050";
  drawScopeCurve(ctx, points, color, "rgba(42,37,32,0.18)", curveProgress);
}

function seek(ratio: number) {
  const audio = audioRef.value;
  if (!audio || !duration.value) return;
  audio.currentTime = ratio * duration.value;
  currentTime.value = audio.currentTime;
  const parent = canvasRef.value?.parentElement;
  if (parent) paint(parent.clientWidth, props.height);
}

function onPointerDown(e: PointerEvent) {
  isDragging.value = true;
  canvasRef.value?.setPointerCapture(e.pointerId);
  seek(ratioFromX(e.clientX));
}

function onPointerMove(e: PointerEvent) {
  if (isDragging.value) seek(ratioFromX(e.clientX));
}

function onPointerUp(e: PointerEvent) {
  isDragging.value = false;
  canvasRef.value?.releasePointerCapture(e.pointerId);
}

function ratioFromX(clientX: number): number {
  const canvas = canvasRef.value;
  if (!canvas) return 0;
  const rect = canvas.getBoundingClientRect();
  return Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
}

function togglePlay() {
  const audio = audioRef.value;
  if (!audio) return;
  if (audio.paused) void audio.play();
  else audio.pause();
}

function bindAudio() {
  const audio = audioRef.value;
  if (!audio) return;
  bindPlaybackHandlers();
  audio.ontimeupdate = () => {
    currentTime.value = audio.currentTime;
    if (!isPlaying.value) {
      const parent = canvasRef.value?.parentElement;
      if (parent) paint(parent.clientWidth, props.height);
    }
  };
  audio.onloadedmetadata = () => {
    duration.value = audio.duration || 0;
  };
}

function animLoop() {
  if (isPlaying.value) {
    const parent = canvasRef.value?.parentElement;
    if (parent) paint(parent.clientWidth, props.height);
  }
  raf = requestAnimationFrame(animLoop);
}

onMounted(() => {
  bindAudio();
  observeResize((w) => {
    void loadPeaks(w).then(() => paint(w, props.height));
  });
  const parent = canvasRef.value?.parentElement;
  if (parent) {
    resize(parent.clientWidth, props.height);
    void loadPeaks(parent.clientWidth).then(() => paint(parent.clientWidth, props.height));
  }
  raf = requestAnimationFrame(animLoop);
});

watch(
  () => mediaSrc.value,
  () => {
    currentTime.value = 0;
    duration.value = 0;
    peaks.value = null;
    bindAudio();
    const parent = canvasRef.value?.parentElement;
    if (parent) {
      void loadPeaks(parent.clientWidth).then(() => paint(parent.clientWidth, props.height));
    }
  },
);

onUnmounted(() => {
  cancelAnimationFrame(raf);
  audioRef.value?.pause();
});

function fmt(sec: number): string {
  if (!Number.isFinite(sec)) return "00:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}
</script>

<template>
  <div class="tape-player">
    <div
      class="tape-player__scope"
      :style="{ height: `${height}px` }"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
    >
      <canvas ref="canvasRef" class="w-full h-full" role="slider" aria-label="波形进度" />
    </div>
    <div class="tape-player__transport">
      <TapeReel :spinning="isPlaying" :size="48" />
      <div class="tape-player__controls">
        <TransportButton
          :variant="isPlaying ? 'pause' : 'play'"
          :label="isPlaying ? '暂停' : '播放'"
          @click="togglePlay"
        />
        <div class="tape-player__timecode rack-label">
          <span>{{ fmt(currentTime) }}</span>
          <span class="tape-player__sep">/</span>
          <span>{{ fmt(duration) }}</span>
        </div>
      </div>
    </div>
    <audio ref="audioRef" :src="mediaSrc" preload="auto" crossorigin="anonymous" class="hidden" />
  </div>
</template>

<style scoped>
.tape-player__scope {
  overflow: hidden;
  border: 1px solid rgba(42, 37, 32, 0.12);
  border-radius: 4px;
  cursor: pointer;
  box-shadow: inset 0 1px 2px rgba(42, 37, 32, 0.06);
}

.tape-player__transport {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-brushed);
}

.tape-player__controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.tape-player__timecode {
  display: flex;
  gap: 4px;
  font-size: 12px;
}

.tape-player__sep {
  opacity: 0.45;
}
</style>
