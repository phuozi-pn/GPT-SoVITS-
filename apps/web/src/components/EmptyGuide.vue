<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 空状态标题 */
    title: string;
    /** 描述文案 */
    desc?: string;
    /** 紧凑模式 */
    compact?: boolean;
    /** 自定义图标（emoji 或 SVG） */
    icon?: string;
  }>(),
  { compact: false, icon: "🌱" },
);
</script>

<template>
  <div class="empty-guide" :class="{ 'empty-guide--compact': compact }">
    <div class="empty-guide__icon-wrapper" aria-hidden="true">
      <span class="empty-guide__icon">{{ icon }}</span>
    </div>
    <h3 class="empty-guide__title">{{ title }}</h3>
    <p v-if="desc" class="empty-guide__desc">{{ desc }}</p>
    <div v-if="$slots.actions" class="empty-guide__actions">
      <slot name="actions" />
    </div>
    <div v-if="$slots.extra" class="empty-guide__extra">
      <slot name="extra" />
    </div>
  </div>
</template>

<style scoped>
.empty-guide {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 48px 32px;
  border: 1px dashed var(--border-glow);
  border-radius: var(--radius-module);
  background: linear-gradient(170deg, var(--bg-surface-muted) 0%, var(--bg-surface) 100%);
  transition: border-color var(--duration-normal) var(--ease-out);
}

.empty-guide:hover {
  border-color: var(--theme-warm-soft);
}

/* prefers-reduced-motion 下的空状态不变色 */
@media (prefers-reduced-motion: reduce) {
  .empty-guide:hover {
    border-color: var(--border-glow);
  }
}

.empty-guide--compact {
  padding: 32px 20px;
}

.empty-guide__icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  margin-bottom: 14px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--bg-surface-raised) 0%, var(--bg-tertiary) 100%);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-inset);
}

.empty-guide__icon {
  font-size: 24px;
  line-height: 1;
  opacity: 0.8;
}

.empty-guide__title {
  margin: 0 0 8px;
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--color-ink);
}

.empty-guide__desc {
  margin: 0 0 20px;
  max-width: 32em;
  font-size: 14px;
  line-height: 1.65;
  color: var(--color-ink-muted);
}

.empty-guide__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}

.empty-guide__extra {
  margin-top: 14px;
  font-size: 12px;
  color: var(--color-brushed-dark);
}
</style>
