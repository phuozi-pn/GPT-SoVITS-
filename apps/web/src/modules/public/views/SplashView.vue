<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";
import { hasAppSession } from "@/utils/session";
import { DEFAULT_WORKBENCH_ROUTE } from "@/architecture/modules";

const router = useRouter();
const phase = ref<"entering" | "revealing" | "exiting">("entering");
const loggedIn = computed(() => hasAppSession());

onMounted(() => {
  // 图标先浮现，标题随后升起
  setTimeout(() => (phase.value = "revealing"), 300);

  // 3 秒后自动跳转
  setTimeout(() => {
    phase.value = "exiting";
    setTimeout(() => {
      router.replace(loggedIn.value ? DEFAULT_WORKBENCH_ROUTE : "/");
    }, 600);
  }, 3000);
});

function skip() {
  phase.value = "exiting";
  setTimeout(() => {
    router.replace(loggedIn.value ? DEFAULT_WORKBENCH_ROUTE : "/");
  }, 400);
}
</script>

<template>
  <div class="splash" :class="`splash--${phase}`" aria-label="Phonia · 品牌序章">
    <!-- 螺旋钻纹图标 — 钻石声源，金色螺旋扩散 -->
    <div class="splash__icon" aria-hidden="true">
      <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M40 30c0-6 4-10 10-8s10 8 6 14-12 8-16 2-2-12 6-14 14 0 14 8" stroke="rgb(200 160 100 / 0.15)" stroke-width="0.6" fill="none"/>
        <path d="M40 28c0-5 3-8 8-6s8 6 4 11-10 6-13 1-1-10 5-11 11 0 11 6" stroke="rgb(200 160 100 / 0.3)" stroke-width="0.8" fill="none"/>
        <path d="M40 22L52 40L40 58L28 40Z" fill="url(#splash-f)" stroke="url(#splash-s)" stroke-width="1.2" transform="rotate(12, 40, 40)"/>
        <path d="M40 22L40 58" stroke="rgb(255 255 255 / 0.07)" stroke-width="0.5" transform="rotate(12, 40, 40)"/>
        <defs>
          <linearGradient id="splash-f" x1="28" y1="40" x2="52" y2="40">
            <stop stop-color="#e8c870"/><stop offset="1" stop-color="#c4923a"/>
          </linearGradient>
          <linearGradient id="splash-s" x1="28" y1="40" x2="52" y2="40">
            <stop stop-color="#f0d080"/><stop offset="1" stop-color="#b08020"/>
          </linearGradient>
        </defs>
      </svg>
    </div>

    <!-- 品牌标题 -->
    <h1 class="splash__title">Phonia</h1>

    <!-- 副标题 -->
    <p class="splash__subtitle">VOICE IDENTITY STUDIO</p>

    <!-- 跳过按钮 -->
    <button class="splash__skip" @click="skip" type="button" :tabindex="phase === 'entering' ? -1 : 0">
      跳过序章
    </button>
  </div>
</template>

<style scoped>
/* ════════════════════════════════════════════════════
   Splash — 品牌序章 · Phonia
   螺旋钻纹：钻石为声源，金色螺旋线旋转扩散
   ════════════════════════════════════════════════════ */

.splash {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0;
  overflow: hidden;
  background: var(--splash-ink-deep);
  transition: background 0.8s var(--ease-molasses);
  cursor: default;
  user-select: none;
}

/* ── 阶段 ────────────────────────────────────── */
.splash--entering { background: var(--bg-secondary); }
.splash--revealing { background: var(--bg-tertiary); }
.splash--exiting {
  background: var(--bg-primary);
  pointer-events: none;
}

/* ── 螺旋钻纹图标 ────────────────────────────── */
.splash__icon {
  width: 80px;
  height: 80px;
  margin-bottom: 28px;
  opacity: 0;
  transform: translateY(16px) scale(0.85);
  transition:
    opacity 1s var(--ease-molasses),
    transform 1s var(--ease-molasses);
  filter: drop-shadow(0 0 20px var(--splash-gold-glow));
}

.splash--revealing .splash__icon {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.splash__icon svg {
  display: block;
  width: 100%;
  height: 100%;
}

/* ── 品牌标题 ────────────────────────────────── */
.splash__title {
  margin: 0 0 14px;
  font-family: var(--brand-font-latin);
  font-size: clamp(3rem, 7vw, 5.5rem);
  font-weight: 600;
  letter-spacing: -0.01em;
  line-height: 1;
  color: var(--brand-phonia-text);
  text-shadow:
    0 0 60px var(--splash-gold-glow),
    0 0 120px var(--splash-gold-dim),
    0 2px 6px rgb(0 0 0 / 0.6);
  opacity: 0;
  transform: translateY(20px);
  transition:
    opacity 0.8s var(--ease-molasses) 0.4s,
    transform 0.8s var(--ease-molasses) 0.4s;
}

.splash--revealing .splash__title {
  opacity: 1;
  transform: translateY(0);
}

/* ── 副标题 ──────────────────────────────────── */
.splash__subtitle {
  margin: 0;
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 400;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: var(--splash-gold-dim);
  opacity: 0;
  transform: translateY(10px);
  transition:
    opacity 0.6s var(--ease-molasses) 0.8s,
    transform 0.6s var(--ease-molasses) 0.8s;
}

.splash--revealing .splash__subtitle {
  opacity: 1;
  transform: translateY(0);
}

/* ── 跳过按钮 ────────────────────────────────── */
.splash__skip {
  position: absolute;
  bottom: 40px;
  right: 48px;
  z-index: 10;
  padding: 8px 18px;
  border: 0.5px solid var(--splash-gold-dim);
  border-radius: var(--radius-ui);
  background: transparent;
  font-family: var(--font-body);
  font-size: 12px;
  letter-spacing: 0.06em;
  color: var(--splash-gold-dim);
  cursor: pointer;
  transition:
    border-color 0.3s var(--ease-out),
    color 0.3s var(--ease-out),
    background 0.3s var(--ease-out),
    opacity 0.5s var(--ease-molasses);
  opacity: 0;
}

.splash--revealing .splash__skip {
  opacity: 1;
  transition-delay: 1.2s;
}

.splash__skip:hover {
  border-color: var(--splash-gold);
  color: var(--splash-gold);
  background: var(--theme-warm-soft);
}

/* ── Exiting 阶段 — 整体淡出 ────────────────── */
.splash--exiting .splash__icon,
.splash--exiting .splash__title,
.splash--exiting .splash__subtitle {
  opacity: 0;
  transform: scale(0.96);
  transition:
    opacity 0.4s var(--ease-out),
    transform 0.4s var(--ease-out);
}

.splash--exiting .splash__skip {
  opacity: 0;
  transition: opacity 0.3s var(--ease-out);
}

/* ── 无障碍 ──────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .splash__icon,
  .splash__title,
  .splash__subtitle,
  .splash__skip {
    transition: none !important;
    opacity: 1 !important;
    transform: none !important;
  }

  .splash {
    transition: none;
    background: var(--bg-tertiary);
  }
}
</style>
