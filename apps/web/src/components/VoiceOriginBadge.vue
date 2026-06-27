<script setup lang="ts">
import { computed } from "vue";
import { resolveVoiceOrigin } from "@/utils/voiceOriginDisplay";

const props = withDefaults(
  defineProps<{
    trainMode?: string | null;
    imported?: boolean;
    size?: "sm" | "md" | "lg";
    showHint?: boolean;
    layout?: "inline" | "stack";
  }>(),
  {
    size: "md",
    showHint: false,
    layout: "inline",
  },
);

const origin = computed(() => resolveVoiceOrigin(props.trainMode, props.imported));
</script>

<template>
  <div
    class="voice-origin-badge"
    :class="[
      origin.badgeClass,
      `voice-origin-badge--${size}`,
      layout === 'stack' ? 'voice-origin-badge--stack' : '',
    ]"
    :title="origin.hint"
  >
    <span class="voice-origin-badge__glyph" aria-hidden="true">{{ origin.glyph }}</span>
    <span class="voice-origin-badge__copy">
      <strong class="voice-origin-badge__label">{{ origin.label }}</strong>
      <span v-if="showHint" class="voice-origin-badge__hint">{{ origin.hint }}</span>
    </span>
  </div>
</template>

<style scoped>
.voice-origin-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
  border-radius: calc(var(--radius-ui) + 2px);
  border: 1px solid transparent;
  font-family: var(--font-sans);
}

.voice-origin-badge--stack {
  align-items: flex-start;
}

.voice-origin-badge__glyph {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border-radius: 10px;
  font-family: var(--font-display);
  font-weight: 700;
  line-height: 1;
}

.voice-origin-badge__copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.voice-origin-badge__label {
  font-weight: 700;
  letter-spacing: 0.02em;
}

.voice-origin-badge__hint {
  font-size: 11px;
  font-weight: 500;
  line-height: 1.35;
  opacity: 0.92;
}

/* ── 快速克隆：暖色高亮 ── */
.voice-origin-badge--clone {
  border-color: color-mix(in srgb, var(--theme-warm) 55%, transparent);
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--theme-warm) 22%, transparent),
    color-mix(in srgb, var(--theme-warm) 8%, transparent)
  );
  color: var(--theme-warm);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--theme-warm) 18%, transparent);
}

.voice-origin-badge--clone .voice-origin-badge__glyph {
  background: color-mix(in srgb, var(--theme-warm) 28%, #000);
  color: #fff;
}

.voice-origin-badge--clone .voice-origin-badge__hint {
  color: color-mix(in srgb, var(--theme-warm) 82%, var(--color-ink));
}

/* ── 微调训练：冷蓝稳重 ── */
.voice-origin-badge--train {
  border-color: color-mix(in srgb, #5b8fd4 50%, transparent);
  background: linear-gradient(
    135deg,
    color-mix(in srgb, #5b8fd4 18%, transparent),
    color-mix(in srgb, #5b8fd4 6%, transparent)
  );
  color: #8eb8ea;
  box-shadow: 0 0 0 1px color-mix(in srgb, #5b8fd4 16%, transparent);
}

.voice-origin-badge--train .voice-origin-badge__glyph {
  background: color-mix(in srgb, #4a7fc4 75%, #0a1420);
  color: #eef5ff;
}

.voice-origin-badge--train .voice-origin-badge__hint {
  color: color-mix(in srgb, #8eb8ea 85%, var(--color-ink-muted));
}

/* ── 导入：中性灰紫 ── */
.voice-origin-badge--import {
  border-color: color-mix(in srgb, #9a8ec8 45%, transparent);
  background: color-mix(in srgb, #9a8ec8 12%, transparent);
  color: #c4b8e8;
}

.voice-origin-badge--import .voice-origin-badge__glyph {
  background: color-mix(in srgb, #7a6eb0 70%, #121018);
  color: #f4f0ff;
}

.voice-origin-badge--dev {
  border-color: var(--border-glow);
  background: var(--bg-surface-muted);
  color: var(--color-ink-muted);
}

.voice-origin-badge--dev .voice-origin-badge__glyph {
  background: var(--bg-surface);
  color: var(--color-ink-muted);
}

/* ── 尺寸 ── */
.voice-origin-badge--sm {
  padding: 4px 8px 4px 4px;
  gap: 6px;
}

.voice-origin-badge--sm .voice-origin-badge__glyph {
  width: 22px;
  height: 22px;
  font-size: 11px;
  border-radius: 7px;
}

.voice-origin-badge--sm .voice-origin-badge__label {
  font-size: 11px;
}

.voice-origin-badge--md {
  padding: 6px 10px 6px 6px;
}

.voice-origin-badge--md .voice-origin-badge__glyph {
  width: 28px;
  height: 28px;
  font-size: 13px;
}

.voice-origin-badge--md .voice-origin-badge__label {
  font-size: 12px;
}

.voice-origin-badge--lg {
  padding: 10px 14px 10px 10px;
  gap: 10px;
}

.voice-origin-badge--lg .voice-origin-badge__glyph {
  width: 36px;
  height: 36px;
  font-size: 16px;
  border-radius: 12px;
}

.voice-origin-badge--lg .voice-origin-badge__label {
  font-size: 14px;
}

.voice-origin-badge--lg .voice-origin-badge__hint {
  font-size: 12px;
}
</style>
