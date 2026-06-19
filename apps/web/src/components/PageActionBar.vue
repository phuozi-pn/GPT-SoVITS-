<script setup lang="ts">
defineProps<{
  label?: string;
}>();
</script>

<template>
  <footer class="page-action-bar">
    <span v-if="label" class="page-action-bar__label">{{ label }}</span>
    <nav class="page-action-bar__nav" aria-label="页面操作">
      <slot />
    </nav>
  </footer>
</template>
