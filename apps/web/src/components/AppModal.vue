<script setup lang="ts">
import { onMounted, onUnmounted, watch } from "vue";

const props = defineProps<{
  open: boolean;
  title: string;
  label?: string;
  wide?: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

function onKeydown(e: KeyboardEvent) {
  if (e.key === "Escape" && props.open) {
    emit("close");
  }
}

watch(
  () => props.open,
  (visible) => {
    document.body.style.overflow = visible ? "hidden" : "";
  },
);

onMounted(() => window.addEventListener("keydown", onKeydown));
onUnmounted(() => {
  window.removeEventListener("keydown", onKeydown);
  document.body.style.overflow = "";
});
</script>

<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="open" class="app-modal-root">
        <button type="button" class="app-modal-backdrop" aria-label="关闭对话框" @click="emit('close')" />
        <div
          class="app-modal"
          :class="{ 'app-modal--wide': wide }"
          role="dialog"
          aria-modal="true"
          :aria-label="title"
        >
          <header class="app-modal__head">
            <div class="app-modal__titles">
              <p v-if="label" class="rack-label">{{ label }}</p>
              <h2 class="rack-title">{{ title }}</h2>
            </div>
            <button type="button" class="app-modal__close" aria-label="关闭" @click="emit('close')">
              ×
            </button>
          </header>
          <div class="app-modal__body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="app-modal__foot">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
