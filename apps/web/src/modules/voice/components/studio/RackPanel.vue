<template>
  <section class="rack-panel" :class="{ 'rack-panel--brushed': brushed }">
    <span v-for="n in 4" :key="n" class="rack-screw" :class="`rack-screw--${['tl', 'tr', 'bl', 'br'][n - 1]}`" aria-hidden="true" />
    <header v-if="title || $slots.head" class="rack-panel__head">
      <slot name="head">
        <div>
          <p v-if="label" class="rack-label">{{ label }}</p>
          <h2 v-if="title" class="rack-title">{{ title }}</h2>
        </div>
      </slot>
      <slot name="actions" />
    </header>
    <div class="rack-panel__body" :class="bodyClass">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  title?: string;
  label?: string;
  brushed?: boolean;
  bodyClass?: string;
}>();
</script>
