<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 骨架块高度 */
    height?: string;
    /** 宽度，默认 100% */
    width?: string;
    /** 圆角 */
    radius?: string;
    /** 是否显示为圆形 */
    circle?: boolean;
    /** 重复行数（用于文本段落） */
    lines?: number;
    /** 行间距 */
    lineGap?: string;
  }>(),
  {
    height: "16px",
    width: "100%",
    radius: "var(--radius-ui)",
    circle: false,
    lines: 1,
    lineGap: "10px",
  },
);
</script>

<template>
  <div
    v-if="lines <= 1"
    class="skeleton-block"
    :class="{ 'skeleton-block--circle': circle }"
    :style="{
      height,
      width: circle ? height : width,
      borderRadius: circle ? '50%' : radius,
    }"
    aria-hidden="true"
  />
  <div
    v-else
    class="skeleton-lines"
    :style="{ gap: lineGap }"
    aria-hidden="true"
    role="presentation"
  >
    <div
      v-for="i in lines"
      :key="i"
      class="skeleton-block"
      :style="{
        height,
        width: i === lines ? '60%' : width,
        borderRadius: radius,
      }"
    />
  </div>
</template>

<style scoped>
.skeleton-block {
  background: linear-gradient(
    110deg,
    var(--bg-surface-muted) 30%,
    var(--bg-surface-glass) 50%,
    var(--bg-surface-muted) 70%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.6s ease-in-out infinite;
}

.skeleton-block--circle {
  flex-shrink: 0;
}

.skeleton-lines {
  display: flex;
  flex-direction: column;
  width: 100%;
}

@keyframes skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton-block {
    animation: none;
    background: var(--bg-surface-muted);
  }
}
</style>
