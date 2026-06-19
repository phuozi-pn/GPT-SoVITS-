<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    spinning?: boolean;
    size?: number;
  }>(),
  {
    spinning: false,
    size: 56,
  },
);

const rotation = ref(0);
const velocity = ref(0);
let raf = 0;
let last = 0;

function loop(ts: number) {
  if (!last) last = ts;
  const dt = Math.min(0.032, (ts - last) / 1000);
  last = ts;

  if (props.spinning) {
    velocity.value = 140;
  } else {
    velocity.value *= Math.exp(-4.5 * dt);
    if (velocity.value < 0.5) velocity.value = 0;
  }
  rotation.value = (rotation.value + velocity.value * dt) % 360;
  raf = requestAnimationFrame(loop);
}

watch(
  () => props.spinning,
  () => {
    last = 0;
  },
);

onMounted(() => {
  raf = requestAnimationFrame(loop);
});

onUnmounted(() => cancelAnimationFrame(raf));
</script>

<template>
  <div class="tape-deck" :style="{ '--reel-size': `${size}px` }">
    <div class="tape-reel" :style="{ transform: `rotate(${rotation}deg)` }">
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <circle cx="32" cy="32" r="30" fill="#D8D2C8" stroke="#2A2520" stroke-width="1.5" />
        <circle cx="32" cy="32" r="22" fill="none" stroke="rgba(42,37,32,0.15)" stroke-width="1" />
        <circle cx="32" cy="32" r="8" fill="#2A2520" />
        <line x1="32" y1="10" x2="32" y2="54" stroke="rgba(42,37,32,0.2)" stroke-width="1" />
        <line x1="10" y1="32" x2="54" y2="32" stroke="rgba(42,37,32,0.2)" stroke-width="1" />
      </svg>
    </div>
    <div class="tape-reel tape-reel--b" :style="{ transform: `rotate(${-rotation * 0.85}deg)` }">
      <svg viewBox="0 0 64 64" aria-hidden="true">
        <circle cx="32" cy="32" r="30" fill="#D8D2C8" stroke="#2A2520" stroke-width="1.5" />
        <circle cx="32" cy="32" r="22" fill="none" stroke="rgba(42,37,32,0.15)" stroke-width="1" />
        <circle cx="32" cy="32" r="8" fill="#2A2520" />
        <line x1="32" y1="10" x2="32" y2="54" stroke="rgba(42,37,32,0.2)" stroke-width="1" />
        <line x1="10" y1="32" x2="54" y2="32" stroke="rgba(42,37,32,0.2)" stroke-width="1" />
      </svg>
    </div>
    <div class="tape-band" aria-hidden="true" />
  </div>
</template>

<style scoped>
.tape-deck {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 8px 0;
}

.tape-reel {
  width: var(--reel-size);
  height: var(--reel-size);
  flex-shrink: 0;
}

.tape-reel svg {
  display: block;
  width: 100%;
  height: 100%;
}

.tape-band {
  position: absolute;
  left: calc(50% - 36px);
  top: 50%;
  width: 72px;
  height: 6px;
  margin-top: -3px;
  background: #2A2520;
  opacity: 0.25;
  border-radius: 1px;
}
</style>
