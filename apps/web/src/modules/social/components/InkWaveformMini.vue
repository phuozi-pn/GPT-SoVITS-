<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";

const props = withDefaults(
  defineProps<{
    active?: boolean;
    width?: number;
    height?: number;
  }>(),
  { active: false, width: 120, height: 28 },
);

const canvasRef = ref<HTMLCanvasElement | null>(null);
let raf = 0;
let t = 0;

function draw() {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = props.width;
  const h = props.height;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  canvas.style.width = `${w}px`;
  canvas.style.height = `${h}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  t += props.active ? 0.06 : 0.015;
  ctx.strokeStyle = props.active ? "rgba(26, 24, 22, 0.55)" : "rgba(26, 24, 22, 0.28)";
  ctx.lineWidth = 0.8;
  ctx.beginPath();
  for (let x = 0; x <= w; x += 2) {
    const amp = props.active ? 10 : 5;
    const y = h / 2 + Math.sin(x * 0.09 + t) * amp * Math.sin(x * 0.02 + t * 0.5);
    if (x === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();

  if (props.active) {
    ctx.strokeStyle = "rgba(184, 90, 80, 0.35)";
    ctx.lineWidth = 0.5;
    ctx.beginPath();
    for (let x = 0; x <= w; x += 2) {
      const y = h / 2 + Math.sin(x * 0.11 + t * 1.2 + 1) * 4;
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }

  raf = requestAnimationFrame(draw);
}

onMounted(() => {
  raf = requestAnimationFrame(draw);
});

onUnmounted(() => {
  cancelAnimationFrame(raf);
});
</script>

<template>
  <canvas ref="canvasRef" class="ink-wave-mini" aria-hidden="true" />
</template>

<style scoped>
.ink-wave-mini {
  display: block;
}
</style>
