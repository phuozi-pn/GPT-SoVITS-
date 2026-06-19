<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { levelToDb, springStep } from "@/utils/spring";

const props = withDefaults(
  defineProps<{
    level?: number;
    active?: boolean;
    label?: string;
  }>(),
  {
    level: 0,
    active: false,
    label: "VU",
  },
);

const canvasRef = ref<HTMLCanvasElement | null>(null);
const ledOn = ref(false);
const spring = ref({ value: 0, velocity: 0 });
const phase = ref(0);
let raf = 0;
let last = 0;
let ledTimer: ReturnType<typeof setTimeout> | null = null;

const targetLevel = computed(() => {
  if (!props.active && props.level <= 0.02) return 0.02;
  const pulse = props.active ? 0.08 * Math.sin(phase.value * 0.06) : 0;
  return Math.min(1, Math.max(0, props.level + pulse));
});

const readoutDb = computed(() => levelToDb(spring.value.value).toFixed(1));

function paint() {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  ctx.clearRect(0, 0, w, h);

  const cx = w / 2;
  const cy = h * 0.78;
  const r = Math.min(w, h) * 0.62;

  // Brushed bezel
  const bezel = ctx.createLinearGradient(0, 0, w, h);
  bezel.addColorStop(0, "#D8D2C8");
  bezel.addColorStop(0.5, "#B8B2A8");
  bezel.addColorStop(1, "#C4BEB4");
  ctx.fillStyle = bezel;
  ctx.beginPath();
  ctx.arc(cx, cy, r + 8, Math.PI, 0);
  ctx.lineTo(cx + r + 8, cy + 4);
  ctx.lineTo(cx - r - 8, cy + 4);
  ctx.closePath();
  ctx.fill();

  // Face
  ctx.fillStyle = "#F2EBE1";
  ctx.beginPath();
  ctx.arc(cx, cy, r, Math.PI, 0);
  ctx.closePath();
  ctx.fill();

  // Scale arc ticks
  const dbMarks = [-20, -10, -7, -5, -3, -1, 0, 1, 2, 3];
  ctx.font = '500 9px "IBM Plex Mono", monospace';
  ctx.fillStyle = "#2A2520";
  ctx.textAlign = "center";
  for (const db of dbMarks) {
    const t = (db + 20) / 23;
    const ang = Math.PI + t * Math.PI;
    const x1 = cx + Math.cos(ang) * (r - 10);
    const y1 = cy + Math.sin(ang) * (r - 10);
    const x2 = cx + Math.cos(ang) * (r - 2);
    const y2 = cy + Math.sin(ang) * (r - 2);
    ctx.strokeStyle = db >= 0 ? "#C75D4D" : "rgba(42,37,32,0.35)";
    ctx.lineWidth = db >= 0 ? 1.5 : 1;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
    if (db % 5 === 0 || db >= 0) {
      const lx = cx + Math.cos(ang) * (r - 22);
      const ly = cy + Math.sin(ang) * (r - 22);
      ctx.fillText(String(db), lx, ly + 3);
    }
  }

  const t = Math.max(0, Math.min(1, (levelToDb(spring.value.value) + 20) / 23));
  const ang = Math.PI + t * Math.PI;
  const overDb = levelToDb(spring.value.value) >= 0;
  const pointerColor = overDb ? "#C75D4D" : "#E8A050";

  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(ang + Math.PI / 2);
  ctx.fillStyle = pointerColor;
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(-3, 8);
  ctx.lineTo(0, -(r - 14));
  ctx.lineTo(3, 8);
  ctx.closePath();
  ctx.fill();
  ctx.restore();

  ctx.fillStyle = "#2A2520";
  ctx.beginPath();
  ctx.arc(cx, cy, 5, 0, Math.PI * 2);
  ctx.fill();

  // LED
  if (ledOn.value || overDb) {
    ctx.fillStyle = overDb ? "#C75D4D" : "#E8A050";
    ctx.shadowColor = ctx.fillStyle as string;
    ctx.shadowBlur = 8;
    ctx.beginPath();
    ctx.arc(cx + r - 18, cy - r + 18, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
  }
}

function loop(ts: number) {
  if (!last) last = ts;
  const dt = Math.min(0.032, (ts - last) / 1000);
  last = ts;
  phase.value = ts;
  spring.value = springStep(spring.value, targetLevel.value, dt);
  const db = levelToDb(spring.value.value);
  if (db >= 0 && !ledOn.value) {
    ledOn.value = true;
    if (ledTimer) clearTimeout(ledTimer);
    ledTimer = setTimeout(() => {
      ledOn.value = false;
    }, 120);
  }
  paint();
  raf = requestAnimationFrame(loop);
}

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  paint();
  raf = requestAnimationFrame(loop);
  resizeObserver = new ResizeObserver(() => paint());
  if (canvasRef.value) resizeObserver.observe(canvasRef.value);
});

onUnmounted(() => {
  resizeObserver?.disconnect();
  cancelAnimationFrame(raf);
  if (ledTimer) clearTimeout(ledTimer);
});
</script>

<template>
  <div class="vu-meter">
    <div class="vu-meter__label rack-label">{{ label }}</div>
    <canvas ref="canvasRef" class="vu-meter__canvas" role="img" :aria-label="`VU 表 ${readoutDb} dB`" />
    <div class="vu-meter__readout">
      <span class="vu-meter__db">{{ readoutDb }}</span>
      <span class="vu-meter__unit">dB</span>
    </div>
  </div>
</template>

<style scoped>
.vu-meter {
  position: relative;
  padding: 8px 8px 4px;
}

.vu-meter__label {
  margin-bottom: 4px;
}

.vu-meter__canvas {
  display: block;
  width: 100%;
  height: 120px;
}

.vu-meter__readout {
  display: flex;
  justify-content: center;
  align-items: baseline;
  gap: 4px;
  margin-top: 4px;
}

.vu-meter__db {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-ink);
}

.vu-meter__unit {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-brushed);
}
</style>
