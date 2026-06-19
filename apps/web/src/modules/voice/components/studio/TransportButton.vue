<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: "play" | "pause" | "record" | "default";
    label?: string;
    busy?: boolean;
    disabled?: boolean;
    size?: "md" | "lg";
  }>(),
  {
    variant: "default",
    busy: false,
    disabled: false,
    size: "md",
  },
);

defineEmits<{ click: [] }>();
</script>

<template>
  <button
    type="button"
    class="transport-btn"
    :class="[
      `transport-btn--${variant}`,
      `transport-btn--${size}`,
      { 'transport-btn--busy': busy },
    ]"
    :disabled="disabled || busy"
    @click="$emit('click')"
  >
    <span class="transport-btn__face">
      <svg v-if="variant === 'play' && !busy" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M8 6v12l10-6L8 6z" stroke="currentColor" stroke-width="2" stroke-linejoin="round" />
      </svg>
      <svg v-else-if="variant === 'pause'" width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M7 6v12M17 6v12" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      </svg>
      <span v-else-if="variant === 'record' && !busy" class="transport-btn__rec-dot" aria-hidden="true" />
      <span v-else-if="busy" class="transport-btn__busy" aria-hidden="true" />
      <slot v-else />
    </span>
    <span v-if="label" class="transport-btn__label">{{ label }}</span>
  </button>
</template>

<style scoped>
.transport-btn {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  padding: 0;
  cursor: pointer;
}

.transport-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.transport-btn__face {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--color-ink);
  border-radius: 4px;
  background: linear-gradient(180deg, #3D3630 0%, #2D2824 100%);
  box-shadow:
    0 1px 0 rgb(255 255 255 / 0.08),
    0 2px 0 rgb(0 0 0 / 0.25);
  color: var(--color-ink);
  transition: box-shadow 0.12s, transform 0.12s;
}

.transport-btn--md .transport-btn__face {
  width: 44px;
  height: 44px;
}

.transport-btn--lg .transport-btn__face {
  width: 52px;
  height: 52px;
}

.transport-btn:not(:disabled):active .transport-btn__face {
  transform: translateY(1px);
  box-shadow:
    inset 0 2px 4px rgba(42, 37, 32, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.transport-btn--record .transport-btn__face {
  background: var(--color-peak-red);
  border-color: var(--color-cinnabar);
  color: #fff;
}

.transport-btn__rec-dot {
  width: 14px;
  height: 14px;
  border-radius: 2px;
  background: #fff;
}

.transport-btn__busy {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(42, 37, 32, 0.2);
  border-top-color: var(--color-ink);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.transport-btn__label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--color-ink);
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
