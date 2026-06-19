<script setup lang="ts">
defineProps<{
  /** 加载提示文案 */
  text?: string;
  /** 紧凑模式（小尺寸，行内显示） */
  inline?: boolean;
}>();
</script>

<template>
  <div
    class="loading-spinner"
    :class="{ 'loading-spinner--inline': inline }"
    role="status"
    aria-live="polite"
  >
    <span class="loading-spinner__ring" aria-hidden="true" />
    <span v-if="text" class="loading-spinner__text">{{ text }}</span>
    <span v-else-if="!inline" class="loading-spinner__text">加载中…</span>
  </div>
</template>

<style scoped>
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px 16px;
}

.loading-spinner--inline {
  flex-direction: row;
  padding: 12px 0;
  gap: 8px;
}

.loading-spinner__ring {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  border: 2.5px solid var(--color-brushed);
  border-top-color: var(--color-vu-amber);
  border-radius: 50%;
  animation: spinner-rotate 0.7s linear infinite;
}

.loading-spinner--inline .loading-spinner__ring {
  width: 18px;
  height: 18px;
}

.loading-spinner__text {
  font-size: 13px;
  color: var(--color-ink-muted);
}

.loading-spinner--inline .loading-spinner__text {
  font-size: 13px;
}

@keyframes spinner-rotate {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .loading-spinner__ring {
    animation: none;
    border-top-color: var(--color-brushed);
    opacity: 0.5;
  }
}
</style>
