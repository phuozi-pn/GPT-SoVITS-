import { ref } from "vue";

export type ToastTone = "ok" | "error" | "warn" | "info";

export interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
  /** 自动消失时长（毫秒），0 表示不自动消失 */
  duration: number;
}

let nextId = 1;

const toasts = ref<ToastItem[]>([]);

export function useToast() {
  function add(message: string, tone: ToastTone = "ok", duration = 4500) {
    const id = nextId++;
    const item: ToastItem = { id, message, tone, duration };
    toasts.value.push(item);
    if (duration > 0) {
      setTimeout(() => {
        remove(id);
      }, duration);
    }
    return id;
  }

  function remove(id: number) {
    const idx = toasts.value.findIndex((t) => t.id === id);
    if (idx >= 0) toasts.value.splice(idx, 1);
  }

  return {
    toasts,
    toast: add,
    dismissToast: remove,
    toastOk: (msg: string) => add(msg, "ok"),
    toastError: (msg: string) => add(msg, "error", 0),
    toastWarn: (msg: string) => add(msg, "warn", 6000),
    toastInfo: (msg: string) => add(msg, "info", 3500),
  };
}
