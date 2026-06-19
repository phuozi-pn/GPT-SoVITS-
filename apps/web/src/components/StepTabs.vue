<script setup lang="ts">
export type StepTab = { n: number; label: string; desc?: string };

defineProps<{
  steps: StepTab[];
  current: number;
  doneUntil?: number;
}>();

const emit = defineEmits<{
  select: [n: number];
}>();
</script>

<template>
  <div class="step-tabs" role="tablist">
    <button
      v-for="s in steps"
      :key="s.n"
      type="button"
      role="tab"
      class="step-tab"
      :class="{
        'step-tab--active': current === s.n,
        'step-tab--done': (doneUntil ?? 0) >= s.n && current !== s.n,
      }"
      :aria-selected="current === s.n"
      @click="emit('select', s.n)"
    >
      <span class="step-tab__num">
        {{ (doneUntil ?? 0) >= s.n && current !== s.n ? "✓" : s.n }}
      </span>
      <span class="step-tab__copy">
        <span class="step-tab__label">{{ s.label }}</span>
        <span v-if="s.desc" class="step-tab__desc">{{ s.desc }}</span>
      </span>
    </button>
  </div>
</template>
