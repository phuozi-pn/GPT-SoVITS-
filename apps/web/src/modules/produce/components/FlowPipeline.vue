<script setup lang="ts">
export type FlowStep = {
  id: string;
  num: string;
  label: string;
  desc: string;
};

withDefaults(
  defineProps<{
    steps: FlowStep[];
    active?: string;
  }>(),
  { active: "" },
);
</script>

<template>
  <ol class="flow-pipeline" aria-label="流程步骤">
    <li
      v-for="step in steps"
      :key="step.id"
      class="flow-pipeline__step reveal-child"
      :class="{ 'flow-pipeline__step--active': active === step.id }"
    >
      <div class="flow-pipeline__meta">
        <span class="flow-pipeline__dot" aria-hidden="true" />
        <span class="flow-pipeline__num">{{ step.num }}</span>
      </div>
      <p class="flow-pipeline__label">{{ step.label }}</p>
      <p class="flow-pipeline__desc">{{ step.desc }}</p>
    </li>
  </ol>
</template>
