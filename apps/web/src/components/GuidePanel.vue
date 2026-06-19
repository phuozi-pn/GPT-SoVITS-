<script setup lang="ts">
export type GuideStep = {
  n: number;
  title: string;
  desc: string;
};

withDefaults(
  defineProps<{
    steps: GuideStep[];
    title?: string;
    compact?: boolean;
    grid?: boolean;
  }>(),
  { compact: false, grid: false },
);
</script>

<template>
  <div class="guide-panel" :class="{ 'guide-panel--compact': compact, 'guide-panel--grid': grid }">
    <h3 v-if="title" class="guide-panel__title">{{ title }}</h3>
    <ol class="guide-steps">
      <li v-for="s in steps" :key="s.n" class="guide-step">
        <span class="guide-step__num" aria-hidden="true">{{ s.n }}</span>
        <div class="guide-step__body">
          <strong class="guide-step__title">{{ s.title }}</strong>
          <p class="guide-step__desc">{{ s.desc }}</p>
          <div v-if="$slots[`step-${s.n}`]" class="guide-step__action">
            <slot :name="`step-${s.n}`" />
          </div>
        </div>
      </li>
    </ol>
  </div>
</template>
