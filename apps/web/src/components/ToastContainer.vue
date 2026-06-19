<script setup lang="ts">
import { useToast } from "@/composables/useToast";

const { toasts, dismissToast } = useToast();
</script>

<template>
  <Teleport to="body">
    <TransitionGroup
      name="toast-list"
      tag="div"
      class="toast-container"
      role="status"
      aria-live="polite"
      aria-label="通知"
    >
      <div
        v-for="t in toasts"
        :key="t.id"
        class="toast-item"
        :class="`toast-item--${t.tone}`"
        role="alert"
      >
        <span class="toast-item__icon" aria-hidden="true">
          <template v-if="t.tone === 'ok'">✓</template>
          <template v-else-if="t.tone === 'error'">✗</template>
          <template v-else-if="t.tone === 'warn'">!</template>
          <template v-else>ℹ</template>
        </span>
        <span class="toast-item__msg">{{ t.message }}</span>
        <button
          v-if="t.duration === 0 || t.duration >= 5000"
          type="button"
          class="toast-item__close"
          aria-label="关闭"
          @click="dismissToast(t.id)"
        >×</button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 18px;
  right: 18px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 380px;
  pointer-events: none;
}

.toast-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--radius-ui);
  font-size: 13px;
  line-height: 1.45;
  pointer-events: auto;
  box-shadow: 0 4px 20px rgb(31 28 25 / 0.12), 0 1px 3px rgb(31 28 25 / 0.06);
  backdrop-filter: blur(6px);
}

.toast-item__icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
}

.toast-item--ok {
  background: rgb(42 37 32 / 0.88);
  color: #e8e2d6;
  border: 1px solid var(--border-glow);
}

.toast-item--ok .toast-item__icon {
  background: rgb(92 156 92 / 0.7);
  color: #fff;
}

.toast-item--error {
  background: rgb(120 60 52 / 0.92);
  color: #ffe6e2;
  border: 1px solid rgb(184 90 80 / 0.35);
}

.toast-item--error .toast-item__icon {
  background: rgb(199 93 77 / 0.7);
  color: #fff;
}

.toast-item--warn {
  background: rgb(160 120 60 / 0.92);
  color: #fff8ee;
  border: 1px solid rgb(232 160 80 / 0.35);
}

.toast-item--warn .toast-item__icon {
  background: rgb(232 160 80 / 0.7);
  color: #fff;
}

.toast-item--info {
  background: rgb(52 56 68 / 0.92);
  color: #e2e6f0;
  border: 1px solid rgb(96 100 120 / 0.25);
}

.toast-item--info .toast-item__icon {
  background: rgb(96 100 120 / 0.5);
  color: #fff;
}

.toast-item__msg {
  flex: 1;
  min-width: 0;
}

.toast-item__close {
  flex-shrink: 0;
  padding: 0;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 4px;
  background: rgb(255 255 255 / 0.1);
  color: inherit;
  font-size: 14px;
  cursor: pointer;
  line-height: 22px;
  text-align: center;
  opacity: 0.6;
  transition: opacity var(--duration-fast) var(--ease-out);
}

.toast-item__close:hover {
  opacity: 1;
}

/* TransitionGroup 动画 */
.toast-list-enter-active {
  transition: all 0.3s var(--ease-spring);
}

.toast-list-leave-active {
  transition: all 0.25s var(--ease-out);
}

.toast-list-enter-from {
  opacity: 0;
  transform: translateX(40px) scale(0.92);
}

.toast-list-leave-to {
  opacity: 0;
  transform: translateX(20px) scale(0.95);
}

.toast-list-move {
  transition: transform 0.3s var(--ease-out);
}
</style>
