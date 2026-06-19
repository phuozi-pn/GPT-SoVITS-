<script setup lang="ts">
defineProps<{
  badge?: string | number;
}>();
</script>

<template>
  <button type="button" class="page-action-link">
    <slot />
    <span v-if="badge != null && badge !== '' && badge !== 0" class="page-action-link__badge">{{ badge }}</span>
  </button>
</template>
