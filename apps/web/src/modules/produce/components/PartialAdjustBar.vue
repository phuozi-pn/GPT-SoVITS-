<script setup lang="ts">
const props = defineProps<{
  selectionLength: number;
  disabled?: boolean;
  globalSpeed?: number;
}>();

const localSpeed = defineModel<number>("localSpeed", { default: 1.05 });
const localPitch = defineModel<number>("localPitch", { default: 1 });

const emit = defineEmits<{ apply: [] }>();
</script>

<template>
  <div v-if="selectionLength > 0" class="partial-bar">
    <p class="partial-bar__title">局部调节 · 已选 {{ selectionLength }} 字</p>
    <p class="partial-bar__hint">
      调好后点「应用到选区」，再点底部「重新生成」试听；音调为后处理变调，语速差异更明显。
      <template v-if="globalSpeed != null">全局语速 {{ globalSpeed.toFixed(2) }}。</template>
    </p>
    <div class="partial-bar__controls">
      <label class="partial-bar__slider">
        <span>语速 {{ localSpeed.toFixed(2) }}</span>
        <input v-model.number="localSpeed" type="range" min="0.5" max="1.5" step="0.05" :disabled="disabled" />
      </label>
      <label class="partial-bar__slider">
        <span>音调 {{ localPitch.toFixed(2) }}</span>
        <input v-model.number="localPitch" type="range" min="0.75" max="1.25" step="0.05" :disabled="disabled" />
      </label>
      <button type="button" class="btn btn-primary btn-sm partial-bar__apply" :disabled="disabled" @click="emit('apply')">
        应用到选区
      </button>
    </div>
  </div>
</template>

<style scoped>
.partial-bar {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid rgb(212 146 74 / 0.25);
  background: var(--color-vu-amber-soft);
}

.partial-bar__title {
  margin: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--theme-warm);
}

.partial-bar__hint {
  margin: 0;
  font-size: 11px;
  line-height: 1.45;
  color: var(--color-ink-muted);
}

.partial-bar__controls {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 12px;
  align-items: end;
}

@media (max-width: 720px) {
  .partial-bar__controls {
    grid-template-columns: 1fr;
  }
}

.partial-bar__slider {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--color-ink-muted);
}

.partial-bar__slider input[type="range"] {
  width: 100%;
  height: 6px;
  padding: 0;
  border: none;
  accent-color: var(--color-vu-amber);
  box-shadow: none;
}

.partial-bar__apply {
  align-self: end;
  white-space: nowrap;
}
</style>
