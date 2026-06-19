import { ref } from "vue";

/** 复制文本到剪贴板，2 秒内显示 copied 状态 */
export function useCopyText() {
  const copied = ref(false);
  let timer: ReturnType<typeof setTimeout> | null = null;

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      copied.value = true;
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => {
        copied.value = false;
      }, 2000);
      return true;
    } catch {
      return false;
    }
  }

  return { copied, copy };
}
