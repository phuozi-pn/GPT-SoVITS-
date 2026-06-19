<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string;
    subtitle?: string;
    eyebrow?: string;
    hint?: string;
    compact?: boolean;
    /** 嵌入 PageSurface 时去掉独立卡片边框 */
    flow?: boolean;
  }>(),
  { compact: false, flow: false },
);
</script>

<template>
  <header
    class="page-header"
    :class="{
      'page-header--compact': compact,
      'page-header--strip': compact,
      'page-header--flow': flow,
    }"
  >
    <div v-if="!compact && (title || eyebrow)" class="page-header__lead">
      <p v-if="eyebrow" class="page-eyebrow">{{ eyebrow }}</p>
      <h1 v-if="title" class="page-title">{{ title }}</h1>
      <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
      <p v-if="hint" class="page-hint">{{ hint }}</p>
    </div>
    <!-- flow 紧凑模式下也显示标题，与 stats/actions 同行 -->
    <div v-if="compact && (title || eyebrow)" class="page-header__lead page-header__lead--compact">
      <p v-if="eyebrow" class="page-eyebrow page-eyebrow--compact">{{ eyebrow }}</p>
      <h2 v-if="title" class="page-header__title">{{ title }}</h2>
    </div>
    <div v-if="$slots.stats" class="page-header__stats">
      <slot name="stats" />
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
    <p v-if="compact && hint" class="page-header__hint">{{ hint }}</p>
  </header>
</template>

<style scoped>
.page-header--compact {
  align-items: center;
  padding: 14px 20px;
  margin-bottom: 0;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-module);
  background: var(--bg-surface-glass);
  backdrop-filter: blur(10px);
  box-shadow: var(--shadow-soft), var(--shadow-inset);
  transition:
    border-color var(--duration-normal) var(--ease-out),
    box-shadow var(--duration-normal) var(--ease-out);
}

.page-header--compact:hover {
  border-color: rgb(184 149 106 / 0.16);
  box-shadow:
    var(--shadow-soft),
    var(--shadow-inset),
    0 0 0 1px rgb(184 149 106 / 0.06);
}

.page-header--flow.page-header--compact {
  border: none;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
  backdrop-filter: none;
  border-bottom: 1px solid var(--border-subtle);
  padding: 20px clamp(18px, 2.4vw, 28px) 18px;
  gap: 12px 16px;
}

.page-header--flow.page-header--compact:hover {
  border-color: var(--border-glow);
  box-shadow: none;
}

.page-header--flow.page-header--compact.page-header--strip {
  gap: 12px 14px;
}

.page-header--compact.page-header--strip {
  flex-wrap: wrap;
  gap: 14px;
}

.page-header__stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  flex: 1;
}

.page-header--compact .page-header__stats {
  justify-content: flex-start;
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.page-header__hint {
  flex: 1 1 100%;
  margin: 0;
  padding-top: 12px;
  border-top: 1px solid var(--border-glow);
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-ink-muted);
}

.page-header--flow .page-header__hint {
  margin-top: 2px;
}

/* ── 紧凑模式下的标题样式 ────────────────── */
.page-header__lead--compact {
  flex-shrink: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.page-header__title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  letter-spacing: -0.01em;
  line-height: 1.3;
  color: var(--color-ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.page-eyebrow--compact {
  margin-bottom: 2px;
  font-size: 9px;
}

.page-hint {
  margin: 10px 0 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--color-ink-muted);
}
</style>
