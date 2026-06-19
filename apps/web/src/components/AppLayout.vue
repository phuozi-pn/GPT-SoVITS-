<script setup lang="ts">
import { computed, ref, watchEffect } from "vue";
import { RouterLink } from "vue-router";
import AppTopBar from "@/components/AppTopBar.vue";
import OnboardingWelcome from "@/components/OnboardingWelcome.vue";
import RequestBar from "@/components/RequestBar.vue";
import ToastContainer from "@/components/ToastContainer.vue";
import { useWorkspaceShell } from "@/composables/useWorkspaceShell";
import { useOnboarding } from "@/composables/useOnboarding";
import { API_DOCS_URL } from "@/config";
import { DEFAULT_ROUTE, PUBLIC_SITE_ROUTE } from "@/config/navigation";

/** 侧栏折叠状态，默认展开；可通过 localStorage 记忆 */
const sidebarCollapsed = ref(
  typeof localStorage !== "undefined" ? localStorage.getItem("phonia-sidebar-collapsed") === "true" : false,
);

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
  localStorage.setItem("phonia-sidebar-collapsed", String(sidebarCollapsed.value));
}

/** 根据视口宽度自动折叠（小屏默认折叠） */
watchEffect(() => {
  if (typeof window === "undefined") return;
  const mq = window.matchMedia("(max-width: 900px)");
  const stored = localStorage.getItem("phonia-sidebar-collapsed");
  if (!stored) {
    sidebarCollapsed.value = mq.matches;
  }
});

const {
  isLogin,
  userPhone,
  devMode,
  devUserId,
  devUserLabel,
  navGroups,
  unreadTotal,
  isActive,
  DEV_USER_PRESETS,
} = useWorkspaceShell();

const { showWelcome, recordFirstLogin, closeWelcome, finishOnboarding, restartOnboarding } = useOnboarding();

// 在组件挂载后检查是否需要记录首次登录
if (!isLogin.value && typeof window !== "undefined") {
  recordFirstLogin();
}

/** 侧栏导航图标映射 — 使用简标文字替代 emoji，保持风格统一 */
const NAV_ICONS: Record<string, string> = {
  library: "🎧",
  projects: "📋",
  studio: "🎙",
  voices: "📁",
  catalog: "🛒",
  discover: "🔍",
  community: "💬",
  admin: "⚙",
};

/** 侧栏底部的快捷帮助链接 */
const helpLinks = computed(() => [
  { to: "/", label: "平台首页" },
  { to: PUBLIC_SITE_ROUTE, label: "公开站点" },
]);
</script>

<template>
  <div v-if="isLogin" class="min-h-screen">
    <slot />
  </div>

  <div v-else class="app-shell" :class="{ 'app-shell--sidebar-collapsed': sidebarCollapsed }">
    <!-- 新手引导弹窗 -->
    <OnboardingWelcome v-if="showWelcome" @close="closeWelcome" />
    <aside class="app-shell__sidebar">
      <button
        type="button"
        class="app-shell__sidebar-toggle"
        :title="sidebarCollapsed ? '展开侧栏' : '折叠侧栏'"
        :aria-label="sidebarCollapsed ? '展开侧栏' : '折叠侧栏'"
        @click="toggleSidebar"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M6 3L11 8L6 13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <RouterLink :to="DEFAULT_ROUTE" class="app-shell__brand">
        <span class="app-shell__brand-mark" aria-hidden="true">
          <svg viewBox="0 0 40 40" fill="none" class="app-shell__brand-mark-svg">
            <path d="M20 15c0-2.5 2-4.5 5-3.5s5 4 3 7-6 4-8 1-1-6 3-7 7 0 7 4" stroke="rgb(255 255 255 / 0.15)" stroke-width="0.7" fill="none"/>
            <path d="M20 11L26 20L20 29L14 20Z" fill="url(#app-diamond-f)" stroke="rgb(255 255 255 / 0.5)" stroke-width="1" transform="rotate(12, 20, 20)"/>
            <defs>
              <linearGradient id="app-diamond-f" x1="14" y1="20" x2="26" y2="20">
                <stop stop-color="#f0d080"/>
                <stop offset="1" stop-color="#c4923a"/>
              </linearGradient>
            </defs>
          </svg>
        </span>
        <span class="app-shell__brand-text">
          <strong>Phonia</strong>
          <span>工作台</span>
        </span>
      </RouterLink>

      <nav class="app-shell__nav" aria-label="主导航">
        <div v-for="group in navGroups" :key="group.id" class="app-shell__nav-group">
          <div class="app-shell__nav-group-head">
            <p class="app-shell__nav-group-label">{{ group.label }}</p>
            <span class="app-shell__nav-group-summary" :title="group.summary">{{ group.summary }}</span>
          </div>
          <RouterLink
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="app-shell__nav-item"
            :class="{ 'app-shell__nav-item--on': isActive(item) }"
          >
            <span class="app-shell__nav-icon" aria-hidden="true">{{ NAV_ICONS[item.name] ?? "→" }}</span>
            <span class="app-shell__nav-copy">
              <span class="app-shell__nav-label">
                {{ item.label }}
                <span
                  v-if="item.name === 'community' && unreadTotal > 0"
                  class="app-shell__nav-badge"
                >
                  {{ unreadTotal > 99 ? "99+" : unreadTotal }}
                </span>
              </span>
              <span class="app-shell__nav-hint">{{ item.hint }}</span>
            </span>
          </RouterLink>
        </div>
      </nav>

      <footer class="app-shell__sidebar-foot">
        <!-- 用户身份区（优先展示） -->
        <div v-if="userPhone && !devMode" class="app-shell__user">
          <div class="app-shell__user-avatar" aria-hidden="true">
            <span class="app-shell__user-initials">{{ userPhone.slice(-2) }}</span>
          </div>
          <div class="app-shell__user-meta">
            <span class="app-shell__user-name">已登录</span>
            <span class="app-shell__user-phone">{{ userPhone }}</span>
          </div>
        </div>

        <!-- 开发者面板 -->
        <details v-if="devMode" class="app-shell__dev">
          <summary class="app-shell__dev-summary">
            <span class="app-shell__dev-tag">开发</span>
            <span class="app-shell__dev-current">{{ devUserLabel }}</span>
          </summary>
          <div class="app-shell__dev-body">
            <span class="rack-label">调试用户</span>
            <select v-model="devUserId">
              <option v-for="u in DEV_USER_PRESETS" :key="u.id" :value="u.id">{{ u.label }}</option>
            </select>
          </div>
        </details>

        <hr class="app-shell__foot-divider" />

        <div class="app-shell__help">
          <RouterLink
            v-for="link in helpLinks"
            :key="link.to"
            :to="link.to"
            class="app-shell__help-link"
          >{{ link.label }}</RouterLink>
          <button
            type="button"
            class="app-shell__help-link app-shell__help-link--action"
            @click="restartOnboarding"
          >新手引导</button>
        </div>

        <a :href="API_DOCS_URL" target="_blank" rel="noreferrer" class="app-shell__doc">API 文档</a>
      </footer>
    </aside>

    <div class="app-shell__main">
      <RequestBar />
      <AppTopBar />
      <main class="app-shell__content">
        <div class="app-shell__slot-frame">
          <slot />
        </div>
      </main>
      <ToastContainer />
      <footer class="app-shell__footer">
        AI 合成语音 · 请确认声纹授权 ·
        <RouterLink :to="PUBLIC_SITE_ROUTE" class="app-shell__footer-link">公开站点</RouterLink>
        ·
        <a :href="API_DOCS_URL" target="_blank" rel="noreferrer">合规说明</a>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex: 1;
  min-height: 0;
}

/* ── 侧栏折叠按钮 ──────────────────────────── */
.app-shell__sidebar-toggle {
  position: absolute;
  top: 14px;
  right: 10px;
  z-index: 41;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border: 1px solid transparent;
  border-radius: var(--radius-ui);
  background: transparent;
  color: var(--color-ink-faint);
  cursor: pointer;
  transition:
    background var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out);
}

.app-shell__sidebar-toggle:hover {
  background: var(--theme-warm-dim);
  border-color: var(--theme-warm-soft);
  color: var(--color-ink);
}

.app-shell__sidebar-toggle svg {
  transition: transform var(--duration-normal) var(--ease-out);
}

/* 折叠时旋转箭头 */
.app-shell--sidebar-collapsed .app-shell__sidebar-toggle svg {
  transform: rotate(180deg);
}

.app-shell__sidebar {
  position: fixed;
  top: 0;
  left: 0;
  z-index: 40;
  display: flex;
  width: 220px;
  height: 100vh;
  flex-direction: column;
  padding: 24px 16px;
  transition:
    width var(--duration-normal) var(--ease-out),
    transform var(--duration-normal) var(--ease-out);
  background-color: #171C22;
  background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='60' height='60' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  overflow-x: hidden;
}

/* ── 折叠状态 ──────────────────────────────── */
.app-shell--sidebar-collapsed .app-shell__sidebar {
  width: 56px;
  padding: 24px 8px;
}

.app-shell--sidebar-collapsed .app-shell__brand-text,
.app-shell--sidebar-collapsed .app-shell__nav-group-head,
.app-shell--sidebar-collapsed .app-shell__nav-hint,
.app-shell--sidebar-collapsed .app-shell__nav-label,
.app-shell--sidebar-collapsed .app-shell__nav-badge,
.app-shell--sidebar-collapsed .app-shell__user-meta,
.app-shell--sidebar-collapsed .app-shell__dev-current,
.app-shell--sidebar-collapsed .app-shell__help,
.app-shell--sidebar-collapsed .app-shell__doc,
.app-shell--sidebar-collapsed .app-shell__foot-divider {
  opacity: 0;
  width: 0;
  height: 0;
  overflow: hidden;
  margin: 0;
  padding: 0;
  pointer-events: none;
  transition:
    opacity var(--duration-fast) var(--ease-out),
    width var(--duration-fast) var(--ease-out),
    height var(--duration-fast) var(--ease-out),
    margin var(--duration-fast) var(--ease-out);
}

.app-shell--sidebar-collapsed .app-shell__brand {
  justify-content: center;
  padding: 10px 4px;
  margin-bottom: 20px;
}

.app-shell--sidebar-collapsed .app-shell__nav-item {
  justify-content: center;
  padding: 10px 4px;
}

.app-shell--sidebar-collapsed .app-shell__nav-icon {
  margin: 0;
}

.app-shell--sidebar-collapsed .app-shell__nav-group {
  gap: 2px;
}

.app-shell--sidebar-collapsed .app-shell__nav {
  gap: 10px;
}

.app-shell--sidebar-collapsed .app-shell__sidebar-foot {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.app-shell--sidebar-collapsed .app-shell__user {
  justify-content: center;
  padding: 8px;
}

.app-shell--sidebar-collapsed .app-shell__dev-summary {
  justify-content: center;
}

.app-shell--sidebar-collapsed .app-shell__main {
  margin-left: 56px;
}

.app-shell--sidebar-collapsed .app-shell__sidebar-toggle {
  right: 4px;
  top: 10px;
}

.app-shell__brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 28px;
  padding: 10px 12px;
  text-decoration: none;
  color: inherit;
  border-radius: var(--radius-module);
  transition:
    background var(--duration-normal) var(--ease-out),
    transform var(--duration-normal) var(--ease-out);
}

.app-shell__brand:hover {
  background: var(--theme-warm-dim);
  transform: translateX(1px);
}

.app-shell__brand-mark {
  display: flex;
  height: 38px;
  width: 38px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--color-highlight) 0%, var(--theme-warm) 100%);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.15),
    0 4px 16px var(--theme-warm-glow);
  transition:
    transform var(--duration-normal) var(--ease-spring),
    box-shadow var(--duration-normal) var(--ease-out);
}

.app-shell__brand-mark-svg {
  display: block;
  width: 20px;
  height: 20px;
}

.app-shell__brand:hover .app-shell__brand-mark {
  transform: scale(1.04);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.2),
    0 6px 20px var(--theme-warm-glow);
}

.app-shell__brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.app-shell__brand-text strong {
  font-family: var(--brand-font-latin);
  font-size: 17px;
  font-weight: 500;
  letter-spacing: -0.01em;
  line-height: 1.2;
  color: var(--color-ink);
}

.app-shell__brand-text span {
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--color-ink-faint);
}

.app-shell__nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow-y: auto;
  padding-right: 2px;
}

.app-shell__nav-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.app-shell__nav-group-head {
  padding: 0 12px;
  margin-bottom: 4px;
}

.app-shell__nav-group-label {
  margin: 0 0 2px;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-brushed-dark);
}

.app-shell__nav-group-summary {
  display: block;
  font-size: 10px;
  line-height: 1.35;
  color: var(--color-ink-faint);
  opacity: 0;
  max-height: 0;
  overflow: hidden;
  transition:
    opacity var(--duration-normal) var(--ease-out),
    max-height var(--duration-normal) var(--ease-out);
}

.app-shell__sidebar:hover .app-shell__nav-group-summary,
.app-shell__sidebar:focus-within .app-shell__nav-group-summary {
  opacity: 1;
  max-height: 2em;
}

.app-shell__nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: none;
  border-radius: var(--radius-ui);
  text-decoration: none;
  color: var(--color-ink-muted);
  transition:
    background var(--duration-normal) var(--ease-out),
    color var(--duration-normal) var(--ease-out);
}

.app-shell__nav-icon {
  flex-shrink: 0;
  width: 20px;
  text-align: center;
  font-size: 14px;
  line-height: 1;
  opacity: 0.65;
  transition: opacity var(--duration-fast) var(--ease-out);
}

.app-shell__nav-item:hover .app-shell__nav-icon,
.app-shell__nav-item--on .app-shell__nav-icon {
  opacity: 1;
}

.app-shell__nav-hint {
  font-size: 11px;
  line-height: 1.4;
  color: var(--color-ink-faint);
  transition: opacity var(--duration-fast) var(--ease-out);
}

/* Compact by default: show hints on hover/focus (keeps "stage" wide) */
.app-shell__sidebar:not(:hover) .app-shell__nav-hint {
  opacity: 0;
  height: 0;
  overflow: hidden;
}

.app-shell__sidebar:focus-within .app-shell__nav-hint,
.app-shell__sidebar:hover .app-shell__nav-hint {
  opacity: 1;
  height: auto;
}

.app-shell__nav-item:hover {
  background: var(--theme-warm-dim);
  color: var(--color-ink);
}

.app-shell__nav-item--on {
  background: var(--theme-warm-soft);
  color: var(--theme-warm);
}

.app-shell__nav-item--on::before {
  content: "";
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 2px;
  border-radius: 1px;
  background: var(--theme-warm);
  opacity: 0.8;
}

.app-shell__nav-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.app-shell__nav-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.01em;
}

.app-shell__nav-badge {
  min-width: 18px;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--theme-warm);
  color: var(--bg-primary);
  font-size: 10px;
  font-weight: 600;
  line-height: 1.45;
  text-align: center;
  animation: badge-pulse 2.4s var(--ease-out) infinite;
}

@keyframes badge-pulse {
  0%,
  100% {
    transform: scale(1);
  }

  50% {
    transform: scale(1.06);
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-shell__brand:hover {
    transform: none;
  }

  .app-shell__brand:hover .app-shell__brand-mark {
    transform: none;
  }

  .app-shell__nav-badge {
    animation: none;
  }
}

.app-shell__sidebar-foot {
  margin-top: auto;
  padding-top: 10px;
}

/* ── 用户身份卡片 ──────────────────────────── */
.app-shell__user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-module);
  background: var(--bg-surface-glass);
  border: 1px solid var(--border-subtle);
  transition:
    border-color var(--duration-normal) var(--ease-out),
    background var(--duration-normal) var(--ease-out);
  cursor: default;
  margin-bottom: 10px;
}

.app-shell__user:hover {
  border-color: var(--border-glow);
  background: var(--bg-surface-raised);
}

.app-shell__user-avatar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 50%;
  background: linear-gradient(135deg, #e0c080 0%, #c4923a 100%);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.2),
    0 2px 8px rgb(196 146 58 / 0.2);
}

.app-shell__user-initials {
  font-family: var(--brand-font-latin);
  font-size: 13px;
  font-weight: 600;
  color: var(--bg-primary);
  letter-spacing: 0.02em;
  line-height: 1;
}

.app-shell__user-meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.app-shell__user-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-ink);
  letter-spacing: 0.01em;
  line-height: 1.3;
}

.app-shell__user-phone {
  font-size: 11px;
  color: var(--color-ink-faint);
  letter-spacing: 0.03em;
  line-height: 1.3;
  font-family: var(--font-mono);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── 底部分割线 ──────────────────────────── */
.app-shell__foot-divider {
  display: none;
}

/* ── 帮助链接 ────────────────────────────── */
.app-shell__help {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  margin-bottom: 4px;
}

.app-shell__help-link {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: var(--radius-ui);
  font-size: 11px;
  color: var(--color-ink-faint);
  text-decoration: none;
  transition:
    background var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out);
}

.app-shell__help-link:hover {
  background: var(--color-xuan-light);
  color: var(--color-ink-muted);
}

.app-shell__help-link--action {
  border: none;
  cursor: pointer;
  font-family: inherit;
}

.app-shell__doc {
  display: inline-block;
  font-size: 11px;
  letter-spacing: 0.02em;
  text-decoration: none;
  color: var(--color-brushed-dark);
  transition: color var(--duration-fast) var(--ease-out);
}

.app-shell__doc:hover {
  color: var(--color-ink-muted);
}

/* ── 开发者面板 ──────────────────────────── */
.app-shell__dev {
  margin-bottom: 10px;
}

.app-shell__dev summary {
  list-style: none;
}

.app-shell__dev summary::-webkit-details-marker {
  display: none;
}

.app-shell__dev-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  cursor: pointer;
  padding: 8px 10px;
  border-radius: var(--radius-ui);
  border: 1px solid var(--color-line);
  background: var(--bg-surface-glass);
  transition:
    border-color var(--duration-normal) var(--ease-out),
    background var(--duration-normal) var(--ease-out);
}

.app-shell__dev-summary:hover {
  border-color: var(--border-glow);
  background: var(--bg-surface-raised);
}

.app-shell__dev-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 7px;
  border-radius: 3px;
  background: var(--color-vu-amber-dim);
  border: 0.5px solid rgb(229 169 60 / 0.22);
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.05em;
  color: var(--theme-warm);
}

.app-shell__dev-current {
  font-size: 12px;
  color: var(--color-ink-faint);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: var(--font-mono);
}

.app-shell__dev-body {
  padding: 10px 10px 0;
}

.app-shell__dev-body select {
  margin-top: 6px;
  font-size: 12px;
}

.app-shell__main {
  display: flex;
  flex-direction: column;
  flex: 1;
  margin-left: 220px;
  padding: 28px 48px 32px;
  min-width: 0;
  min-height: 0;
}

.app-shell__content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.app-shell__slot-frame {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  min-width: 0;
  width: 100%;
  height: 100%;
}

/* 穿透到 slot 内容，确保路由视图撑满 */
.app-shell__slot-frame :deep(> *) {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  min-width: 0;
}

.app-shell__footer {
  padding-top: 18px;
  border-top: none;
  font-size: 11px;
  letter-spacing: 0.03em;
  color: var(--color-brushed-dark);
}

.app-shell__footer a,
.app-shell__footer-link {
  color: inherit;
  text-decoration: underline;
  text-underline-offset: 3px;
}

@media (max-width: 900px) {
  .app-shell__sidebar {
    width: 212px;
    padding: 20px 12px;
  }

  .app-shell__main {
    margin-left: 212px;
    padding: 20px 20px 16px;
  }

  .app-shell__sidebar:not(:hover) .app-shell__nav-hint {
    opacity: 0;
    height: 0;
  }
}
</style>
