<script setup lang="ts">
import { ref } from "vue";

withDefaults(
  defineProps<{
    /** 提示标题 */
    title?: string;
    /** 提示正文 */
    text: string;
    /** 图标 */
    icon?: string;
    /** 是否可关闭 */
    closable?: boolean;
    /** 颜色主题 */
    tone?: "info" | "warn" | "tip";
  }>(),
  {
    closable: false,
    tone: "info",
    icon: "💡",
  },
);

const closed = ref(false);
</script>

<template>
  <div
    v-if="!closed"
    class="help-hint"
    :class="`help-hint--${tone}`"
    role="status"
  >
    <span class="help-hint__icon" aria-hidden="true">{{ icon }}</span>
    <div class="help-hint__body">
      <strong v-if="title" class="help-hint__title">{{ title }}</strong>
      <p class="help-hint__text">{{ text }}</p>
    </div>
    <button
      v-if="closable"
      class="help-hint__close"
      aria-label="关闭提示"
      type="button"
      @click="closed = true"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <line x1="18" y1="6" x2="6" y2="18" />
        <line x1="6" y1="6" x2="18" y2="18" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.help-hint {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: var(--radius-ui);
  font-size: 13px;
  line-height: 1.6;
}

.help-hint--info {
  border: 1px solid rgb(110 152 196 / 0.25);
  background: rgb(110 152 196 / 0.08);
  color: #8bb8e0;
}

.help-hint--warn {
  border: 1px solid rgb(212 146 74 / 0.35);
  background: rgb(212 146 74 / 0.08);
  color: #e0b060;
}

.help-hint--tip {
  border: 1px solid rgb(76 168 104 / 0.25);
  background: rgb(76 168 104 / 0.08);
  color: #7ec892;
}

.help-hint__icon {
  flex-shrink: 0;
  font-size: 16px;
  line-height: 1.4;
  opacity: 0.85;
}

.help-hint__body {
  flex: 1;
  min-width: 0;
}

.help-hint__title {
  display: block;
  margin-bottom: 4px;
  font-size: 13px;
  font-weight: 600;
}

.help-hint__text {
  margin: 0;
  font-size: 12px;
}

.help-hint__close {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: none;
  border-radius: var(--radius-ui);
  background: transparent;
  color: inherit;
  opacity: 0.5;
  cursor: pointer;
}

.help-hint__close:hover {
  opacity: 1;
  background: rgb(255 255 255 / 0.06);
}
</style>
