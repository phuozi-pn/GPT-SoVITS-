<script setup lang="ts">
defineProps<{
  message: string;
  /** 是否显示重试按钮 */
  retry?: boolean;
  /** 是否正在重试中 */
  loading?: boolean;
}>();

const emit = defineEmits<{
  retry: [];
  dismiss: [];
}>();
</script>

<template>
  <div class="error-banner" role="alert">
    <span class="error-banner__icon" aria-hidden="true">✗</span>
    <span class="error-banner__msg">{{ message }}</span>
    <button
      v-if="retry"
      type="button"
      class="error-banner__action"
      :disabled="loading"
      @click="emit('retry')"
    >
      {{ loading ? "重试中…" : "重试" }}
    </button>
    <button
      type="button"
      class="error-banner__dismiss"
      aria-label="关闭"
      @click="emit('dismiss')"
    >×</button>
  </div>
</template>

<style scoped>
.error-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  border: 1px solid rgb(199 93 77 / 0.35);
  border-radius: var(--radius-ui);
  background: rgb(199 93 77 / 0.1);
  font-size: 14px;
  line-height: 1.5;
  color: var(--color-cinnabar);
  margin-bottom: 16px;
}

.error-banner__icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgb(199 93 77 / 0.2);
  font-size: 11px;
  font-weight: 700;
  color: #9e4538;
}

.error-banner__msg {
  flex: 1;
  min-width: 0;
}

.error-banner__action {
  flex-shrink: 0;
  padding: 3px 12px;
  border: 1px solid rgb(199 93 77 / 0.35);
  border-radius: var(--radius-ui);
  background: var(--bg-surface-glass);
  color: var(--color-cinnabar);
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  transition:
    background var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out);
}

.error-banner__action:hover:not(:disabled) {
  background: rgb(199 93 77 / 0.15);
  border-color: rgb(199 93 77 / 0.5);
}

.error-banner__action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-banner__dismiss {
  flex-shrink: 0;
  padding: 0;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 4px;
  background: rgb(199 93 77 / 0.08);
  color: inherit;
  font-size: 14px;
  cursor: pointer;
  line-height: 22px;
  text-align: center;
  opacity: 0.6;
  transition: opacity var(--duration-fast) var(--ease-out);
}

.error-banner__dismiss:hover {
  opacity: 1;
}
</style>
