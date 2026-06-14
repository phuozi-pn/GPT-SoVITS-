<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";

const route = useRoute();
const isLogin = computed(() => route.name === "login");
const userPhone = computed(() => localStorage.getItem("user_phone") ?? "");
const devMode = computed(() => localStorage.getItem("dev_mode") === "1");
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell--login': isLogin }">
    <header v-if="!isLogin" class="app-header">
      <div class="app-header__inner">
        <RouterLink to="/studio" class="brand">
          <span class="brand__mark" aria-hidden="true">🎙</span>
          <span class="brand__text">
            <strong>Voice Studio</strong>
            <small>语音克隆工作台</small>
          </span>
        </RouterLink>
        <nav class="app-nav">
          <RouterLink to="/studio" class="app-nav__link">工作室</RouterLink>
          <RouterLink to="/library" class="app-nav__link">音色库</RouterLink>
          <RouterLink to="/projects" class="app-nav__link">批量配音</RouterLink>
          <a href="/api/v1/docs" target="_blank" rel="noreferrer" class="app-nav__link">API</a>
        </nav>
        <div class="app-header__meta">
          <span v-if="devMode" class="badge badge--warn">开发模式</span>
          <span v-else-if="userPhone" class="badge">{{ userPhone }}</span>
        </div>
      </div>
    </header>

    <main class="app-main" :class="{ 'app-main--login': isLogin }">
      <slot />
    </main>

    <footer v-if="!isLogin" class="app-footer">
      <p>
        本服务生成内容为 AI 合成语音 · 使用前请确认声纹授权 ·
        <a href="/api/v1/docs" target="_blank" rel="noreferrer">合规说明见 API 文档</a>
      </p>
    </footer>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-shell--login {
  background: linear-gradient(145deg, #1e1b4b 0%, #312e81 45%, #0f172a 100%);
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(15, 23, 42, 0.92);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.app-header__inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 1.25rem;
  height: var(--header-h);
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  text-decoration: none;
  color: #fff;
  flex-shrink: 0;
}

.brand:hover {
  text-decoration: none;
  opacity: 0.92;
}

.brand__mark {
  font-size: 1.35rem;
  line-height: 1;
}

.brand__text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand__text strong {
  font-size: 0.95rem;
  letter-spacing: 0.02em;
}

.brand__text small {
  font-size: 0.72rem;
  opacity: 0.65;
  font-weight: 400;
}

.app-nav {
  display: flex;
  gap: 0.25rem;
  flex: 1;
}

.app-nav__link {
  padding: 0.4rem 0.75rem;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  transition: background 0.15s, color 0.15s;
}

.app-nav__link:hover,
.app-nav__link.router-link-active {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
  text-decoration: none;
}

.app-header__meta {
  flex-shrink: 0;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.9);
}

.badge--warn {
  background: rgba(217, 119, 6, 0.25);
  color: #fcd34d;
}

.app-main {
  flex: 1;
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 2rem;
}

.app-main--login {
  max-width: none;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.app-footer {
  border-top: 1px solid var(--border);
  background: var(--surface);
  padding: 0.85rem 1.25rem;
  text-align: center;
}

.app-footer p {
  margin: 0;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.app-footer a {
  color: var(--primary);
}
</style>
