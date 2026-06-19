<script setup lang="ts">
defineProps<{
  busy?: boolean;
  disabled?: boolean;
  aiAck?: boolean;
  generateLabel?: string;
  compact?: boolean;
}>();

const emit = defineEmits<{
  generate: [];
  "update:aiAck": [value: boolean];
}>();

const ack = defineModel<boolean>("aiAck", { default: true });
</script>

<template>
  <div class="action-bar" :class="{ 'action-bar--compact': compact }">
    <!-- 确认 -->
    <label class="action-bar__ack">
      <span class="ack-box">
        <input v-model="ack" type="checkbox" :disabled="busy" />
        <span class="ack-box__visual" aria-hidden="true">
          <span v-if="ack" class="ack-box__check">✓</span>
        </span>
      </span>
      <span class="ack-text">
        已确认合成告知义务
      </span>
    </label>

    <!-- 主按钮 -->
    <button
      type="button"
      class="action-btn"
      :disabled="disabled || busy || !ack"
      @click="emit('generate')"
    >
      <!-- 录制指示 -->
      <span v-if="!busy" class="action-btn__dot" aria-hidden="true" />

      <!-- 合成中 -->
      <span v-if="busy" class="action-btn__spinner" aria-hidden="true" />

      <span class="action-btn__text">
        {{ busy ? "正在合成…" : (generateLabel ?? "开始生成语音") }}
      </span>

      <kbd v-if="!busy && !compact" class="action-btn__kbd">Ctrl+Enter</kbd>
    </button>
  </div>
</template>

<style scoped>
.action-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px 16px;
  padding: 10px 18px;
  background: linear-gradient(180deg, var(--color-xuan-light), var(--color-xuan-warm));
  border-top: 1px solid var(--color-line-strong);
}

.action-bar--compact {
  flex-direction: column;
  align-items: stretch;
  padding: 14px 16px;
}

/* ── 确认 ──────────────────────────────────────────── */
.action-bar__ack {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.ack-box { position: relative; display: flex; align-items: center; }

.ack-box input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.ack-box__visual {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border: 1.5px solid rgb(20 19 18 / 0.15);
  border-radius: 4px;
  background: var(--color-surface);
  transition: all var(--duration-fast) var(--ease-out);
}

.ack-box input:checked + .ack-box__visual {
  background: var(--color-success);
  border-color: var(--color-success);
}

.ack-box input:focus-visible + .ack-box__visual {
  box-shadow: 0 0 0 3px var(--color-success-soft);
}

.ack-box__check {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  line-height: 1;
}

.ack-text {
  font-size: 12px;
  color: var(--color-ink-muted);
  line-height: 1.4;
}

/* ── 主按钮 ────────────────────────────────────────── */
.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-width: 0;
  padding: 7px 14px;
  border: 1px solid rgb(170 120 50 / 0.4);
  border-radius: 7px;
  background: linear-gradient(180deg, #d4a44a 0%, var(--color-vu-amber) 100%);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.02em;
  cursor: pointer;
  white-space: nowrap;
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.22),
    0 1px 0 rgb(140 100 40 / 0.25),
    0 3px 10px rgb(180 130 50 / 0.12);
  transition: all var(--duration-normal) var(--ease-out);
}

.action-btn:hover:not(:disabled) {
  filter: brightness(1.04);
  transform: translateY(-1px);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.28),
    0 2px 0 rgb(140 100 40 / 0.2),
    0 6px 16px rgb(180 130 50 / 0.16);
}

.action-btn:active:not(:disabled) {
  transform: translateY(0);
  box-shadow:
    inset 0 2px 4px rgb(140 100 40 / 0.25),
    0 0 0 rgb(140 100 40 / 0);
}

.action-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
}

.action-btn:focus-visible {
  outline: none;
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.2),
    0 1px 0 rgb(140 100 40 / 0.25),
    0 0 0 3px rgb(180 130 50 / 0.2);
}

.action-bar--compact .action-btn {
  width: 100%;
  min-width: 0;
}

.action-btn__dot {
  width: 9px;
  height: 9px;
  flex-shrink: 0;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 0 0 2px rgb(255 255 255 / 0.25);
  animation: dot-breathe 2.5s ease-in-out infinite;
}

@keyframes dot-breathe {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.action-btn__spinner {
  width: 15px;
  height: 15px;
  border: 2px solid rgb(255 255 255 / 0.25);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.action-btn__text {
  position: relative;
  z-index: 1;
}

.action-btn__kbd {
  padding: 2px 6px;
  border: 1px solid rgb(255 255 255 / 0.25);
  border-radius: 3px;
  background: rgb(255 255 255 / 0.1);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: rgb(255 255 255 / 0.75);
  line-height: 1.3;
}
</style>
