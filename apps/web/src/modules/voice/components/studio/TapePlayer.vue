<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { resolveMediaUrl } from "@/config";
import { readTimeDomain, useAudioAnalyser } from "@/composables/useAudioAnalyser";
import { useCanvasWaveform } from "@/composables/useCanvasWaveform";
import {
  fetchAudioPeaks,
  peaksToScopePoints,
  timeDomainToScopePoints,
} from "@/utils/audioWaveform";
import { buildScopePoints, drawPaperGrid, drawScopeCurve, drawStudioGrid, seedFromText } from "@/utils/oscilloscope";
import TapeReel from "@/modules/voice/components/studio/TapeReel.vue";
import TransportButton from "@/modules/voice/components/studio/TransportButton.vue";

const props = withDefaults(
  defineProps<{
    src: string;
    height?: number;
    /** paper = catalog/light; studio = dark rack */
    theme?: "paper" | "studio";
    /** Hide tape reels — compact inline transport */
    compact?: boolean;
  }>(),
  { height: 88, theme: "paper", compact: false },
);

const isStudio = computed(() => props.theme === "studio");

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
  if (isStudio.value) drawStudioGrid(ctx, w, h);
  else drawPaperGrid(ctx, w, h);

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
    const seed = seedFromText(mediaSrc.value);
    points = buildScopePoints(w, h, seed, currentTime.value * 12, peaksError.value ? 0.35 : 0.9, 1);
    curveProgress = progress.value;
  }
  const color = peaksError.value
    ? "rgba(199, 93, 77, 0.9)"
    : isStudio.value
      ? "#E8A050"
      : "#E8A050";
  const muted = isStudio.value ? "rgb(232 160 80 / 0.38)" : "rgba(42,37,32,0.18)";
  drawScopeCurve(ctx, points, color, muted, curveProgress);
}
function scopeWidth(): number {
  return canvasRef.value?.parentElement?.clientWidth ?? 0;
}

function repaint() {
  const w = scopeWidth();
  if (w <= 0) return;
  resize(w, props.height);
  paint(w, props.height);
}

function scheduleRepaint() {
  void loadPeaks(scopeWidth()).then(() => repaint());
}

function seek(ratio: number) {
  const audio = audioRef.value;
  if (!audio || !duration.value) return;
  audio.currentTime = ratio * duration.value;
  currentTime.value = audio.currentTime;
  repaint();
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
    if (!isPlaying.value) repaint();
  };
  audio.onloadedmetadata = () => {
    duration.value = audio.duration || 0;
    scheduleRepaint();
  };
}

function animLoop() {
  if (isPlaying.value) repaint();
  raf = requestAnimationFrame(animLoop);
}

onMounted(async () => {
  bindAudio();
  observeResize((w) => {
    if (w <= 0) return;
    resize(w, props.height);
    void loadPeaks(w).then(() => paint(w, props.height));
  });
  await nextTick();
  requestAnimationFrame(() => scheduleRepaint());
  raf = requestAnimationFrame(animLoop);
});

watch(
  () => mediaSrc.value,
  () => {
    currentTime.value = 0;
    duration.value = 0;
    peaks.value = null;
    bindAudio();
    scheduleRepaint();
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
  <div class="tape-player" :class="{ 'tape-player--studio': isStudio, 'tape-player--compact': compact }">
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
      <TapeReel v-if="!compact" :spinning="isPlaying" :size="isStudio ? 40 : 48" />
      <div class="tape-player__controls">
        <TransportButton
          :variant="isPlaying ? 'pause' : 'play'"
          :label="compact ? undefined : isPlaying ? '暂停' : '播放'"
          :size="compact ? 'md' : 'md'"
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
.tape-player {
  width: 100%;
}

.tape-player__scope {
  width: 100%;
  overflow: hidden;
  border: 1px solid rgba(42, 37, 32, 0.12);
  border-radius: 4px;
  cursor: pointer;
  box-shadow: inset 0 1px 2px rgba(42, 37, 32, 0.06);
}

.tape-player--studio .tape-player__scope {
  border: 1px solid var(--border-glow, rgb(255 255 255 / 0.1));
  border-radius: var(--radius-ui, 8px);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.04);
  background: rgb(14 16 20 / 0.6);
}

.tape-player__transport {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-brushed);
}

.tape-player--studio .tape-player__transport {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--surface-line, rgb(255 255 255 / 0.08));
}

.tape-player--compact .tape-player__transport {
  margin-top: 8px;
  padding-top: 0;
  border-top: none;
  gap: 10px;
}

.tape-player__controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.tape-player--compact .tape-player__controls {
  gap: 12px;
  flex: 1;
}

.tape-player__timecode {
  display: flex;
  gap: 4px;
  font-size: 12px;
}

.tape-player--studio .tape-player__timecode {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--color-ink-muted);
}

.tape-player__sep {
  opacity: 0.45;
}
</style>
