<script setup lang="ts">
export type ProduceScene = "single" | "dialogue" | "vocal";

const scene = defineModel<ProduceScene>("scene", { default: "single" });

const items: { id: ProduceScene; label: string; hint: string; disabled?: boolean }[] = [
  { id: "single", label: "单人朗读", hint: "长文 / 旁白 · 不切段 · 一个音色" },
  { id: "dialogue", label: "多人情景", hint: "剧本对话 · 多角色多音色" },
  { id: "vocal", label: "歌曲分段", hint: "歌词念唱 · 多声线（实验）" },
];
</script>

<template>
  <div class="produce-scenes" role="tablist" aria-label="制作场景">
    <button
      v-for="item in items"
      :key="item.id"
      type="button"
      role="tab"
      class="produce-scenes__item"
      :class="{ 'produce-scenes__item--on': scene === item.id }"
      :aria-selected="scene === item.id"
      :disabled="item.disabled"
      @click="scene = item.id"
    >
      <span class="produce-scenes__label">{{ item.label }}</span>
      <span class="produce-scenes__hint">{{ item.hint }}</span>
    </button>
  </div>
</template>

<style scoped>
.produce-scenes {
  display: grid;
  gap: 8px;
  margin-bottom: 16px;
}

@media (min-width: 720px) {
  .produce-scenes {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.produce-scenes__item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-ui);
  background: var(--color-surface);
  text-align: left;
  cursor: pointer;
}

.produce-scenes__item--on {
  border-color: var(--color-line-strong);
  box-shadow: var(--shadow-soft);
}

.produce-scenes__item:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.produce-scenes__label {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-ink);
}

.produce-scenes__hint {
  font-size: 12px;
  line-height: 1.45;
  color: var(--color-ink-muted);
}
</style>
