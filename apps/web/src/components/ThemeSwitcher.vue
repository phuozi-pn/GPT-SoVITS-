<script setup lang="ts">
import { computed } from "vue";
import { useTheme } from "@/composables/useTheme";
import type { ThemeMode } from "@/utils/theme";

withDefaults(
  defineProps<{
    /** 页脚/角落实用布局：单行胶囊，弱化边框 */
    compact?: boolean;
  }>(),
  {
    compact: false,
  },
);

const { state, presets, setMode, setCustomBg } = useTheme();

const isCustom = computed(() => state.value.mode === "custom");

function onPresetClick(mode: ThemeMode) {
  setMode(mode);
}

function onColorInput(event: Event) {
  const value = (event.target as HTMLInputElement).value;
  setCustomBg(value);
}
</script>

<template>
  <div class="theme-switcher" :class="{ 'theme-switcher--compact': compact }">
    <div class="theme-switcher__row">
      <span class="theme-switcher__label">{{ compact ? "外观" : "背景主题" }}</span>
      <div class="theme-switcher__presets" role="group" :aria-label="compact ? '外观' : '背景主题'">
        <button
          v-for="preset in presets"
          :key="preset.id"
          type="button"
          class="theme-switcher__btn"
          :class="{ 'theme-switcher__btn--on': state.mode === preset.id }"
          :aria-pressed="state.mode === preset.id"
          @click="onPresetClick(preset.id)"
        >
          {{ preset.label }}
        </button>
      </div>
    </div>
    <p v-if="isCustom && !compact" class="theme-switcher__hint">文字颜色会随背景自动调节对比度</p>
    <label v-if="isCustom" class="theme-switcher__custom">
      <span v-if="!compact">背景色</span>
      <input
        type="color"
        :value="state.customBg"
        aria-label="自定义背景颜色"
        @input="onColorInput"
      />
      <code v-if="!compact">{{ state.customBg }}</code>
    </label>
  </div>
</template>

<style scoped>
.theme-switcher {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.theme-switcher__row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.theme-switcher__label {
  margin: 0;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-ink-faint);
}

.theme-switcher__presets {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
}

.theme-switcher__btn {
  padding: 6px 8px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-ui);
  background: var(--bg-surface);
  font-size: 12px;
  color: var(--color-ink-muted);
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out);
}

.theme-switcher__btn:hover {
  border-color: var(--theme-warm-soft);
  color: var(--color-ink);
}

.theme-switcher__btn--on {
  border-color: var(--theme-warm);
  background: var(--theme-warm-dim);
  color: var(--theme-warm);
  font-weight: 600;
}

.theme-switcher__hint {
  margin: 0;
  font-size: 11px;
  line-height: 1.4;
  color: var(--color-ink-faint);
}

.theme-switcher__custom {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--color-ink-muted);
}

.theme-switcher__custom input[type="color"] {
  width: 32px;
  height: 28px;
  padding: 2px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-ui);
  background: var(--bg-surface);
  cursor: pointer;
}

.theme-switcher__custom code {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-ink-faint);
  background: transparent;
  padding: 0;
}

/* 页脚/登录角：单行胶囊，融入背景 */
.theme-switcher--compact {
  gap: 6px;
}

.theme-switcher--compact .theme-switcher__row {
  flex-direction: row;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 8px 10px;
}

.theme-switcher--compact .theme-switcher__label {
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0;
  text-transform: none;
  color: var(--color-ink-muted);
}

.theme-switcher--compact .theme-switcher__presets {
  display: inline-flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 4px;
  padding: 3px;
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  background: var(--bg-surface-muted);
}

.theme-switcher--compact .theme-switcher__btn {
  padding: 4px 10px;
  border: 1px solid transparent;
  border-radius: 999px;
  background: transparent;
  font-size: 11px;
}

.theme-switcher--compact .theme-switcher__btn:hover {
  background: var(--color-indigo-soft);
}

.theme-switcher--compact .theme-switcher__btn--on {
  border-color: var(--color-line-strong);
  background: var(--color-surface);
  color: var(--color-ink);
  box-shadow: var(--shadow-soft);
}

.theme-switcher--compact .theme-switcher__custom {
  justify-content: center;
  margin-top: 2px;
}

.theme-switcher--compact .theme-switcher__custom input[type="color"] {
  width: 28px;
  height: 24px;
}
</style>
