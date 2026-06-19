/**
 * 水墨涟漪 — 点击时从触点扩散墨韵波纹
 * 纯 CSS 动画 + DOM 管理，零运行时开销
 */
import { onMounted, onUnmounted, ref, type Ref } from "vue";

interface Ripple {
  id: number;
  x: number;
  y: number;
  size: number;
}

const RIPPLE_DURATION = 900; // ms
const MAX_RIPPLES = 6; // 同时最多 6 个涟漪
const RIPPLE_CLASS = "ink-ripple-touch";

let nextId = 0;

export function useInkRipple(containerRef?: Ref<HTMLElement | null>) {
  const ripples = ref<Ripple[]>([]);
  let target: HTMLElement | Document = document;

  function createRippleElement(r: Ripple): HTMLDivElement {
    const el = document.createElement("div");
    el.className = RIPPLE_CLASS;
    el.style.setProperty("--rx", `${r.x}px`);
    el.style.setProperty("--ry", `${r.y}px`);
    el.style.setProperty("--rs", `${r.size}px`);
    el.setAttribute("data-ripple-id", String(r.id));
    return el;
  }

  function handleClick(e: MouseEvent) {
    const size = Math.max(window.innerWidth, window.innerHeight) * 2;
    const ripple: Ripple = {
      id: nextId++,
      x: e.clientX,
      y: e.clientY,
      size,
    };

    ripples.value = [...ripples.value.slice(-(MAX_RIPPLES - 1)), ripple];
    const el = createRippleElement(ripple);
    document.body.appendChild(el);

    // 动画结束后移除 DOM
    setTimeout(() => {
      el.remove();
      ripples.value = ripples.value.filter((r) => r.id !== ripple.id);
    }, RIPPLE_DURATION + 50);
  }

  onMounted(() => {
    target = (containerRef?.value as HTMLElement) ?? document;
    target.addEventListener("click", handleClick);
  });

  onUnmounted(() => {
    target.removeEventListener("click", handleClick);
  });

  return { ripples };
}
