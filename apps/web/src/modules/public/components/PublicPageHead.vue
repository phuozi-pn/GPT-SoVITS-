<script setup lang="ts">
defineProps<{
  title: string;
  hint?: string;
}>();
</script>

<template>
  <header class="showcase-browse__head">
    <div>
      <h1 class="showcase-browse__title">{{ title }}</h1>
      <p v-if="hint" class="hint">{{ hint }}</p>
      <slot name="metrics" />
    </div>
    <div v-if="$slots.actions" class="hero-actions">
      <slot name="actions" />
    </div>
  </header>
</template>
