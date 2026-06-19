<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { PUBLIC_NAV } from "@/architecture/modules";
import { DEFAULT_WORKBENCH_ROUTE } from "@/architecture/modules";
import { hasAppSession } from "@/utils/session";

const route = useRoute();
const loggedIn = computed(() => hasAppSession());
</script>

<template>
  <div class="public-shell">
    <header class="public-shell__header deco-hairline-drift">
      <RouterLink to="/" class="public-shell__brand">
        <span class="public-shell__mark" aria-hidden="true">
          <svg viewBox="0 0 32 32" fill="none" class="public-shell__mark-svg">
            <path d="M16 12c0-2 1.5-3.5 4-3s4 3 2.5 5.5-5 3-6.5 1-1-5 2.5-5.5 5.5 0 5.5 3" stroke="rgb(196 146 58 / 0.3)" stroke-width="0.6" fill="none"/>
            <path d="M16 9L20 16L16 23L12 16Z" fill="#c4923a" stroke="#b08020" stroke-width="0.5" transform="rotate(12, 16, 16)"/>
          </svg>
        </span>
        <span class="public-shell__brand-text">Phonia</span>
      </RouterLink>

      <nav class="public-shell__nav" aria-label="主导航">
        <RouterLink
          v-for="item in PUBLIC_NAV"
          :key="item.path"
          :to="item.path"
          class="public-shell__link"
          :class="{ 'public-shell__link--on': route.name === item.name }"
        >
          {{ item.label }}
        </RouterLink>
      </nav>

      <div class="public-shell__actions">
        <RouterLink v-if="loggedIn" :to="DEFAULT_WORKBENCH_ROUTE" class="public-shell__cta">
          工作台
        </RouterLink>
        <template v-else>
          <RouterLink to="/login" class="public-shell__link">登录</RouterLink>
          <RouterLink to="/login" class="public-shell__cta">开始使用</RouterLink>
        </template>
      </div>
    </header>

    <main class="public-shell__main">
      <slot />
    </main>

    <footer class="public-shell__footer">
      <div class="public-shell__footer-inner">
        <div class="public-shell__footer-brand">
          <span class="public-shell__footer-mark" aria-hidden="true">P</span>
          <p>Phonia · 声音创作工坊</p>
        </div>
        <nav class="public-shell__footer-nav" aria-label="页脚导航">
          <RouterLink to="/browse">音色馆</RouterLink>
          <RouterLink to="/updates">社区</RouterLink>
          <RouterLink :to="loggedIn ? DEFAULT_WORKBENCH_ROUTE : '/login'">
            {{ loggedIn ? "工作台" : "登录" }}
          </RouterLink>
        </nav>
        <p class="public-shell__note">请仅使用已授权声纹 · 合成内容须标注 AI 生成</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.public-shell {
  display: flex;
  min-height: 100vh;
  flex-direction: column;
  background: transparent; /* 依赖全局装饰层 */
}

/* ── Header ──────────────────────────────────────── */
.public-shell__header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 20px;
  padding: 16px clamp(20px, 4vw, 48px);
  border-bottom: 1px solid var(--border-glow);
  background: var(--bg-surface-glass);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  position: sticky;
  top: 0;
  z-index: 50;
}

.public-shell__brand {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  color: inherit;
}

.public-shell__brand-text {
  font-family: var(--brand-font-latin);
  font-size: 18px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.public-shell__mark {
  display: flex;
  width: 32px;
  height: 32px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-ui);
  background: var(--color-surface);
}

.public-shell__mark-svg {
  display: block;
  width: 18px;
  height: 18px;
}

.public-shell__nav {
  display: flex;
  flex: 1;
  justify-content: center;
  gap: 2px;
}

.public-shell__link {
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-ink-muted);
  text-decoration: none;
  border-radius: var(--radius-ui);
  transition:
    color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out);
}

.public-shell__link:hover {
  color: var(--color-ink);
  background: var(--color-indigo-soft);
}

.public-shell__link--on {
  color: var(--color-ink);
  background: var(--color-vu-amber-soft);
}

.public-shell__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.public-shell__cta {
  padding: 9px 18px;
  border: 1px solid rgb(139 105 20 / 0.35);
  border-radius: var(--radius-ui);
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  color: var(--color-vu-amber-deep);
  background: var(--color-vu-amber-soft);
  transition:
    background var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}

.public-shell__cta:hover {
  background: var(--color-vu-amber-glow);
  border-color: rgb(139 105 20 / 0.5);
  transform: translateY(-1px);
}

/* ── Main ────────────────────────────────────────── */
.public-shell__main {
  flex: 1;
  width: 100%;
  max-width: var(--page-max);
  margin: 0 auto;
  padding: clamp(32px, 5vw, 56px) clamp(20px, 4vw, 48px);
}

/* ── Footer ──────────────────────────────────────── */
.public-shell__footer {
  padding: 0;
  border-top: 1px solid var(--color-line);
  background: var(--color-xuan-warm);
}

.public-shell__footer-inner {
  max-width: var(--page-max);
  margin: 0 auto;
  padding: 40px clamp(20px, 4vw, 48px) 32px;
  text-align: center;
}

.public-shell__footer-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.public-shell__footer-mark {
  display: flex;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-ui);
  font-family: var(--font-scroll);
  font-size: 16px;
  font-weight: 600;
  color: var(--color-brushed-dark);
  background: var(--color-surface);
}

.public-shell__footer-brand p {
  margin: 0;
  font-family: var(--font-scroll);
  font-size: 14px;
  color: var(--color-ink-muted);
}

.public-shell__footer-nav {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-bottom: 20px;
}

.public-shell__footer-nav a {
  font-size: 13px;
  color: var(--color-ink-muted);
  text-decoration: none;
  transition: color var(--duration-fast) var(--ease-out);
}

.public-shell__footer-nav a:hover {
  color: var(--color-ink);
}

.public-shell__note {
  margin: 0;
  font-size: 11px;
  color: var(--color-ink-faint);
  letter-spacing: 0.03em;
}
</style>
