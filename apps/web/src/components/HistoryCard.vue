<script setup lang="ts">
import OscilloscopeDisplay from "@/modules/voice/components/studio/OscilloscopeDisplay.vue";

defineProps<{
  title: string;
  subtitle?: string;
  textPreview?: string;
  audioUrl?: string;
  createdAt?: string;
}>();

defineEmits<{ select: [] }>();
</script>

<template>
  <button type="button" class="history-item" @click="$emit('select')">
    <div class="history-item__head">
      <span class="history-item__time rack-label">{{ createdAt }}</span>
      <span class="history-item__title">{{ title }}</span>
    </div>
    <p v-if="textPreview" class="history-item__quote">「{{ textPreview }}」</p>
    <div class="history-item__scope">
      <OscilloscopeDisplay :src="audioUrl" :height="32" />
    </div>
  </button>
</template>

<style scoped>
.history-item {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--color-brushed);
  border-radius: var(--radius-module);
  background: var(--bg-surface-glass);
  text-align: left;
  cursor: pointer;
  color: inherit;
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.04);
  transition: border-color 0.15s, transform 0.15s;
}

.history-item:hover {
  border-color: var(--color-vu-amber);
  transform: translateY(-1px);
}

.history-item:active {
  transform: translateY(0);
  box-shadow: inset 0 2px 4px rgb(0 0 0 / 0.15);
}

.history-item__head {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.history-item__title {
  font-size: 14px;
  font-weight: 600;
}

.history-item__quote {
  margin: 8px 0 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: var(--color-brushed-dark);
}

.history-item__scope {
  margin-top: 8px;
  overflow: hidden;
  border-radius: var(--radius-ui);
}
</style>
