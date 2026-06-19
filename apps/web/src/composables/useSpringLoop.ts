import { onUnmounted, ref, watch, type Ref } from "vue";
import { springStep, type SpringState } from "@/utils/spring";

export function useSpringLoop(target: Ref<number>, onTick?: (value: number) => void) {
  const state = ref<SpringState>({ value: 0, velocity: 0 });
  let raf = 0;
  let last = 0;

  function loop(ts: number) {
    if (!last) last = ts;
    const dt = Math.min(0.032, (ts - last) / 1000);
    last = ts;
    state.value = springStep(state.value, target.value, dt);
    onTick?.(state.value.value);
    raf = requestAnimationFrame(loop);
  }

  watch(
    target,
    () => {
      cancelAnimationFrame(raf);
      last = 0;
      raf = requestAnimationFrame(loop);
    },
    { immediate: true },
  );

  onUnmounted(() => cancelAnimationFrame(raf));

  return state;
}
