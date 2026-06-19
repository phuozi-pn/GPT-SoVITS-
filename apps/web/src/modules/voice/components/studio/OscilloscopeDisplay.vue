<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";
import { readTimeDomain } from "@/composables/useAudioAnalyser";
import { useCanvasWaveform } from "@/composables/useCanvasWaveform";
import { resolveMediaUrl } from "@/config";
import {
  fetchAudioPeaks,
  idleScopePoints,
  peaksToScopePoints,
  timeDomainToScopePoints,
} from "@/utils/audioWaveform";
import { drawPaperGrid, drawScopeCurve } from "@/utils/oscilloscope";

const props = withDefaults(
  defineProps<{
    /** Audio URL — decodes to real waveform peaks */
    src?: string;
    height?: number;
    progress?: number;
    /** When true, read live time-domain from liveAudio each frame */
    live?: boolean;
    liveAudio?: HTMLAudioElement | null;
  }>(),
  {
    height: 100,
    progress: 1,
    live: false,
    liveAudio: null,
  },
);

const canvasRef = ref<HTMLCanvasElement | null>(null);
const { resize, observeResize } = useCanvasWaveform(canvasRef);
const peaks = ref<Float32Array | null>(null);
const loadError = ref(false);
let raf = 0;
let loadToken = 0;

async function loadPeaks(width: number) {
  if (!props.src) {
    peaks.value = null;
    loadError.value = false;
    return;
  }
  const token = ++loadToken;
  loadError.value = false;
  try {
    const count = Math.max(96, Math.floor(width / 2));
    const data = await fetchAudioPeaks(resolveMediaUrl(props.src), count);
    if (token === loadToken) peaks.value = data;
  } catch {
    if (token === loadToken) {
      peaks.value = null;
      loadError.value = true;
    }
  }
}

function paint(w: number, h: number) {
  const ctx = canvasRef.value?.getContext("2d");
  if (!ctx || w <= 0) return;
  drawPaperGrid(ctx, w, h);

  let points: { x: number; y: number }[] = [];
  let curveProgress = props.progress;

  if (props.live && props.liveAudio) {
    const td = readTimeDomain(props.liveAudio);
    if (td) {
      points = timeDomainToScopePoints(w, h, td);
      curveProgress = 1;
    }
  }

  if (!points.length && peaks.value) {
    points = peaksToScopePoints(w, h, peaks.value, props.progress);
    curveProgress = props.progress;
  }

  if (!points.length) {
    points = idleScopePoints(w, h);
    curveProgress = 1;
  }

  const color = loadError.value ? "rgba(199, 93, 77, 0.85)" : "#E8A050";
  drawScopeCurve(ctx, points, color, "rgba(42,37,32,0.18)", curveProgress);
}

function startLoop() {
  cancelAnimationFrame(raf);
  const tick = () => {
    const parent = canvasRef.value?.parentElement;
    if (parent) paint(parent.clientWidth, props.height);
    if (props.live && props.liveAudio) raf = requestAnimationFrame(tick);
  };
  if (props.live && props.liveAudio) raf = requestAnimationFrame(tick);
}

onMounted(() => {
  observeResize((w) => {
    void loadPeaks(w).then(() => paint(w, props.height));
  });
  const parent = canvasRef.value?.parentElement;
  if (parent) {
    resize(parent.clientWidth, props.height);
    void loadPeaks(parent.clientWidth).then(() => paint(parent.clientWidth, props.height));
  }
  startLoop();
});

watch(
  () => [props.src, props.progress, props.live, props.liveAudio],
  () => {
    const parent = canvasRef.value?.parentElement;
    if (parent) {
      void loadPeaks(parent.clientWidth).then(() => paint(parent.clientWidth, props.height));
    }
    startLoop();
  },
);

onUnmounted(() => cancelAnimationFrame(raf));
</script>

<template>
  <div class="scope-wrap" :style="{ height: `${height}px` }">
    <canvas ref="canvasRef" class="scope-canvas" role="img" aria-label="示波器波形" />
  </div>
</template>

<style scoped>
.scope-wrap {
  overflow: hidden;
  border: 1px solid rgba(42, 37, 32, 0.12);
  border-radius: 4px;
  box-shadow: inset 0 1px 2px rgba(42, 37, 32, 0.06);
}
.scope-canvas {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
