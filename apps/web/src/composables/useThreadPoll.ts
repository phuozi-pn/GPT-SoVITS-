import { onUnmounted, watch, type Ref } from "vue";

/** 打开会话时轮询新消息，模拟实时 IM */
export function useThreadPoll(
  peerId: Ref<string>,
  onPoll: () => void | Promise<void>,
  intervalMs = 5000,
) {
  let timer: ReturnType<typeof setInterval> | null = null;

  function stop() {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  watch(
    peerId,
    (id) => {
      stop();
      if (!id) return;
      timer = setInterval(() => void onPoll(), intervalMs);
    },
    { immediate: true },
  );

  onUnmounted(stop);

  return { stop };
}
