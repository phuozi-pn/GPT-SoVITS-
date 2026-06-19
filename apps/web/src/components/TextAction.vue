<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: "default" | "accent" | "danger";
    disabled?: boolean;
    type?: "button" | "submit";
  }>(),
  { variant: "default", type: "button" },
);
</script>

<template>
  <button
    :type="type"
    class="text-action"
    :class="{
      'text-action--accent': variant === 'accent',
      'text-action--danger': variant === 'danger',
    }"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>
