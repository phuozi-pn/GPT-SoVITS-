import { onMounted, onUnmounted, ref, watch, type Ref } from "vue";

export function useCanvasWaveform(canvasRef: Ref<HTMLCanvasElement | null>) {
  const dpr = ref(1);

  function resize(width: number, height: number) {
    const canvas = canvasRef.value;
    if (!canvas) return { width: 0, height: 0 };
    dpr.value = window.devicePixelRatio || 1;
    canvas.width = Math.floor(width * dpr.value);
    canvas.height = Math.floor(height * dpr.value);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    const ctx = canvas.getContext("2d");
    if (ctx) ctx.setTransform(dpr.value, 0, 0, dpr.value, 0, 0);
    return { width, height, ctx };
  }

  function observeResize(onResize: (w: number, h: number) => void) {
    const canvas = canvasRef.value;
    if (!canvas?.parentElement) return;

    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      onResize(width, height);
    });
    ro.observe(canvas.parentElement);

    onUnmounted(() => ro.disconnect());
  }

  return { dpr, resize, observeResize };
}

export function useAnimationFrame(active: Ref<boolean>, tick: (ts: number) => void) {
  let raf = 0;

  function loop(ts: number) {
    tick(ts);
    if (active.value) raf = requestAnimationFrame(loop);
  }

  watch(
    active,
    (on) => {
      cancelAnimationFrame(raf);
      if (on) raf = requestAnimationFrame(loop);
    },
    { immediate: true },
  );

  onUnmounted(() => cancelAnimationFrame(raf));
}
