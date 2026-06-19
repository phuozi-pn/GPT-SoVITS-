<script setup lang="ts">
defineProps<{
  label: string;
}>();
</script>

<template>
  <div class="detail-strip__item">
    <dt class="detail-strip__label">{{ label }}</dt>
    <dd class="detail-strip__value"><slot /></dd>
  </div>
</template>
