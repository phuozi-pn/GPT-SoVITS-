<script setup lang="ts">
/**
 * 全局请求 loading 指示器 — 顶部丝滑进度条。
 *
 * 当有 API 请求进行中时自动显示动画进度条，
 * 所有请求完成后平滑消失。
 * 非阻塞，不影响页面交互。
 */

import { useRequestLoading } from "@/composables/useRequestLoading";

const { loading } = useRequestLoading();
</script>

<template>
  <div class="request-bar" :class="{ 'request-bar--active': loading }" aria-hidden="true">
    <div class="request-bar__track" />
  </div>
</template>

<style scoped>
.request-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  height: 2px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s ease-out;
}

.request-bar--active {
  opacity: 1;
}

.request-bar__track {
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    var(--theme-warm) 0%,
    var(--color-highlight) 50%,
    var(--theme-warm) 100%
  );
  transform-origin: left center;
  animation: request-bar-slide 1.8s ease-in-out infinite;
}

@keyframes request-bar-slide {
  0% {
    transform: scaleX(0);
    transform-origin: left center;
  }
  25% {
    transform: scaleX(0.4);
  }
  50% {
    transform: scaleX(0.7);
    transform-origin: right center;
  }
  75% {
    transform: scaleX(0.95);
  }
  100% {
    transform: scaleX(0);
    transform-origin: left center;
  }
}

@media (prefers-reduced-motion: reduce) {
  .request-bar__track {
    animation: none;
    opacity: 0.7;
  }
}
</style>
