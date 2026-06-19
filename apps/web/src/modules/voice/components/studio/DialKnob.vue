<script setup lang="ts">
import { computed, ref, watch } from "vue";

const props = withDefaults(
  defineProps<{
    modelValue?: number;
    min?: number;
    max?: number;
    step?: number;
    label?: string;
    unit?: string;
  }>(),
  {
    modelValue: 1,
    min: 0.5,
    max: 1.5,
    step: 0.05,
    unit: "",
  },
);

const emit = defineEmits<{ "update:modelValue": [v: number] }>();

const dragging = ref(false);
const startY = ref(0);
const startVal = ref(0);

const display = computed(() => props.modelValue.toFixed(2));

const rotation = computed(() => {
  const t = (props.modelValue - props.min) / (props.max - props.min);
  return -135 + t * 270;
});

function onPointerDown(e: PointerEvent) {
  dragging.value = true;
  startY.value = e.clientY;
  startVal.value = props.modelValue;
  (e.target as HTMLElement).setPointerCapture(e.pointerId);
}

function onPointerMove(e: PointerEvent) {
  if (!dragging.value) return;
  const dy = startY.value - e.clientY;
  const next = startVal.value + dy * props.step * 0.05;
  const clamped = Math.min(props.max, Math.max(props.min, Math.round(next / props.step) * props.step));
  emit("update:modelValue", clamped);
}

function onPointerUp(e: PointerEvent) {
  dragging.value = false;
  (e.target as HTMLElement).releasePointerCapture(e.pointerId);
}
</script>

<template>
  <div class="dial">
    <p v-if="label" class="dial__label rack-label">{{ label }}</p>
    <div
      class="dial__knob"
      :style="{ transform: `rotate(${rotation}deg)` }"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
    >
      <span class="dial__indicator" />
    </div>
    <p class="dial__readout rack-label">{{ display }}{{ unit }}</p>
  </div>
</template>

<style scoped>
.dial {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.dial__knob {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 2px solid var(--color-ink);
  background: linear-gradient(135deg, #D8D2C8 0%, #B8B2A8 50%, #C8C2B8 100%);
  box-shadow:
    0 2px 0 rgba(42, 37, 32, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.45);
  cursor: ns-resize;
  touch-action: none;
  position: relative;
}

.dial__indicator {
  position: absolute;
  top: 6px;
  left: 50%;
  width: 2px;
  height: 12px;
  margin-left: -1px;
  background: var(--color-ink);
  border-radius: 1px;
}

.dial__readout {
  font-size: 11px;
}
</style>
