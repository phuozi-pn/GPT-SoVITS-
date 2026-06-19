<script setup lang="ts">
import { ref, watch } from "vue";

const props = defineProps<{
  open: boolean;
  title: string;
  message: string;
  /** 确认按钮文案 */
  confirmLabel?: string;
  /** 确认按钮色调：danger / warn */
  tone?: "danger" | "warn";
  /** 是否正在执行中 */
  loading?: boolean;
  /** 危险操作时要求输入特定文本确认（可选） */
  confirmText?: string;
}>();

const emit = defineEmits<{
  close: [];
  confirm: [];
}>();

const inputValue = ref("");

watch(
  () => props.open,
  (v) => {
    if (!v) inputValue.value = "";
  },
);
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="open" class="app-modal-root">
        <button type="button" class="app-modal-backdrop" aria-label="关闭" @click="emit('close')" />
        <div
          class="app-modal app-modal--confirm"
          role="alertdialog"
          aria-modal="true"
          :aria-label="title"
        >
          <header class="app-modal__head">
            <div class="app-modal__titles">
              <h2 class="rack-title" :class="{ 'rack-title--danger': tone === 'danger' }">
                {{ title }}
              </h2>
            </div>
          </header>

          <div class="app-modal__body">
            <p class="confirm-modal__msg">{{ message }}</p>
            <label v-if="confirmText" class="field confirm-modal__field">
              <span>请输入 <code>{{ confirmText }}</code> 以确认</span>
              <input
                v-model="inputValue"
                :placeholder="`输入 ${confirmText}`"
                autocomplete="off"
              />
            </label>
          </div>

          <footer class="app-modal__foot">
            <button type="button" class="btn btn--ghost btn--sm" @click="emit('close')">取消</button>
            <button
              type="button"
              class="btn btn--sm"
              :class="tone === 'danger' ? 'btn--warn' : 'btn--primary'"
              :disabled="loading || (confirmText ? inputValue.trim() !== confirmText : false)"
              @click="emit('confirm')"
            >
              {{ confirmLabel ?? "确认" }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.app-modal--confirm {
  max-width: 420px;
}

.confirm-modal__msg {
  margin: 0;
  font-size: 14px;
  line-height: 1.55;
  color: var(--color-ink-muted);
}

.confirm-modal__field {
  margin-top: 16px;
}

.confirm-modal__field input {
  margin-top: 4px;
}

.rack-title--danger {
  color: var(--color-cinnabar);
}
</style>
