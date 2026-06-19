<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { APP_MODULES, DEFAULT_WORKBENCH_ROUTE } from "@/architecture/modules";
import { hasAppSession } from "@/utils/session";

const router = useRouter();
const loggedIn = computed(() => hasAppSession());
const heroReady = ref(false);

onMounted(() => {
  // 延迟一帧触发 Hero 动画，确保 DOM 已挂载
  requestAnimationFrame(() => {
    heroReady.value = true;
  });
});

const entryModules = computed(() =>
  APP_MODULES.filter((m) => m.id !== "ops").map((module) => ({
    ...module,
    primary: module.routes.find((r) => r.requiresAuth && !r.path.includes(":")) ?? module.routes[0],
  })),
);

function go(path: string) {
  if (loggedIn.value) {
    router.push(path);
    return;
  }
  router.push({ path: "/login", query: { redirect: path } });
}
</script>

<template>
  <div class="home">
    <!-- Hero 区域 — 金线流光 + 卷轴文字动画 -->
    <section class="home__hero deco-gold-sweep" :class="{ 'is-ready': heroReady }">
      <div class="home__hero-inner">
        <p class="home__eyebrow">
          <span class="deco-cinnabar-dot" aria-hidden="true" />
          VOICE IDENTITY STUDIO
        </p>
        <h1 class="home__title">Phonia</h1>
        <p class="home__lead">
          一人一音，一文一声。声纹克隆与文本转语音：
          短剧批量出片、多人情景对话、歌曲分段念唱。
        </p>
        <div class="home__actions">
          <button
            type="button"
            class="home__btn home__btn--primary deco-breath-glow"
            @click="go(DEFAULT_WORKBENCH_ROUTE)"
          >
            {{ loggedIn ? "进入工作台" : "免费开始使用" }}
          </button>
          <router-link to="/browse" class="home__btn home__btn--ghost">浏览音色馆</router-link>
        </div>
      </div>

      <!-- Hero 底部装饰线 -->
      <hr class="deco-scroll-rule" aria-hidden="true" />
    </section>

    <!-- 核心工作流速览 — 瀑布入场 -->
    <section class="home__flow" aria-label="工作流">
      <h2 class="home__section-title">核心工作流</h2>
      <div class="home__flow-cards">
        <div class="home__flow-card cascade-item" @click="go('/studio')">
          <span class="home__flow-num">壹</span>
          <div>
            <h3>训练音色</h3>
            <p>上传干声，克隆声纹</p>
          </div>
        </div>
        <span class="home__flow-arrow">→</span>
        <div class="home__flow-card cascade-item" @click="go('/library')">
          <span class="home__flow-num">贰</span>
          <div>
            <h3>智能配音</h3>
            <p>输入文本，一键合成</p>
          </div>
        </div>
        <span class="home__flow-arrow">→</span>
        <div class="home__flow-card cascade-item">
          <span class="home__flow-num">叁</span>
          <div>
            <h3>导出使用</h3>
            <p>WAV / ZIP 下载</p>
          </div>
        </div>
      </div>
      <p class="home__flow-hint">
        也可以从 <router-link to="/browse">音色馆</router-link> 直接购买授权音色，跳过训练。
      </p>
    </section>

    <!-- 使用场景对比 -->
    <section class="home__scenarios" aria-label="使用场景">
      <h2 class="home__section-title">创作场景</h2>
      <div class="home__scenario-grid">
        <article class="home__scenario-card cascade-item">
          <h3 class="home__scenario-title">短剧批量出片</h3>
          <p class="home__scenario-desc">
            准备 CSV 文件（角色名 + 台词），为每个角色绑定音色，一键合成上百行对白。
          </p>
          <button type="button" class="text-action" @click="go('/projects')">短剧批量配音 →</button>
        </article>
        <article class="home__scenario-card cascade-item">
          <h3 class="home__scenario-title">有声书 · 文章朗读</h3>
          <p class="home__scenario-desc">
            粘贴长文本，选择音色，调整语速与情感参数，生成完整朗读。
          </p>
          <button type="button" class="text-action" @click="go('/library')">智能配音 →</button>
        </article>
        <article class="home__scenario-card cascade-item">
          <h3 class="home__scenario-title">多人情景对话</h3>
          <p class="home__scenario-desc">
            粘贴剧本，自动识别角色分段，为每个角色指派不同音色，生成完整对话。
          </p>
          <button type="button" class="text-action" @click="go('/library')">多人情景 →</button>
        </article>
        <article class="home__scenario-card cascade-item">
          <h3 class="home__scenario-title">创作者上架音色</h3>
          <p class="home__scenario-desc">
            训练音色后通过质检，上架音色馆，获得授权收益分成。
          </p>
          <button type="button" class="text-action" @click="go('/studio')">训练工作台 →</button>
        </article>
      </div>
    </section>

    <!-- 常见问题 -->
    <section class="home__faq" aria-label="常见问题">
      <h2 class="home__section-title">常见问题</h2>
      <dl class="home__faq-list">
        <div class="home__faq-item cascade-item">
          <dt>没有自己的录音素材怎么办？</dt>
          <dd>可以从音色馆购买已上架的授权音色，无需自己训练，直接用于合成。</dd>
        </div>
        <div class="home__faq-item cascade-item">
          <dt>训练一个音色需要多久？</dt>
          <dd>上传约 8–10 分钟干声后，GPU 训练通常需要 30 分钟到 2 小时，取决于素材质量和服务器负载。</dd>
        </div>
        <div class="home__faq-item cascade-item">
          <dt>合成需要什么硬件？</dt>
          <dd>无需本地 GPU——合成由云端引擎完成，你只需要浏览器即可。</dd>
        </div>
        <div class="home__faq-item cascade-item">
          <dt>生成的音频可以商用吗？</dt>
          <dd>使用授权音色生成的音频可商用。上架音色时需提交声纹授权证明，由平台审核。</dd>
        </div>
      </dl>
    </section>

    <!-- 底部 CTA -->
    <section class="home__cta deco-gold-sweep">
      <h2 class="home__cta-title">准备好开始了吗？</h2>
      <p class="home__cta-desc">无需下载，浏览器打开即用。几分钟内出片。</p>
      <button
        type="button"
        class="home__btn home__btn--primary home__btn--lg"
        @click="go(DEFAULT_WORKBENCH_ROUTE)"
      >
        {{ loggedIn ? "进入工作台" : "免费注册开始" }}
      </button>
    </section>
  </div>
</template>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: var(--section-gap);
  padding-bottom: 40px;
}

/* ---- Hero ---- */
.home__hero {
  padding-bottom: 32px;
  position: relative;
}

.home__hero-inner {
  position: relative;
}

.home__eyebrow {
  margin: 0 0 12px;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--color-brushed-dark);
  display: flex;
  align-items: center;
  gap: 8px;
  opacity: 0;
  transform: translateY(12px);
  transition:
    opacity 0.6s var(--ease-molasses),
    transform 0.6s var(--ease-molasses);
}

.is-ready .home__eyebrow {
  opacity: 1;
  transform: translateY(0);
}

.home__title {
  margin: 0 0 16px;
  font-family: var(--brand-font-latin);
  font-size: clamp(2.5rem, 6vw, 4.5rem);
  font-weight: 600;
  letter-spacing: -0.01em;
  line-height: 1.1;
  background: linear-gradient(
    135deg,
    var(--color-ink) 0%,
    var(--color-ink-muted) 40%,
    var(--color-sunset) 70%,
    var(--color-ink-muted) 100%
  );
  background-size: 200% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  opacity: 0;
  transform: translateY(16px);
  transition:
    opacity 0.7s var(--ease-molasses) 0.1s,
    transform 0.7s var(--ease-molasses) 0.1s,
    background-position 3s var(--ease-breath) 1s;
}

.is-ready .home__title {
  opacity: 1;
  transform: translateY(0);
  background-position: 100% 0;
}

.home__lead {
  margin: 0 0 28px;
  max-width: 42em;
  font-size: clamp(0.95rem, 1.5vw, 1.1rem);
  line-height: 1.85;
  color: var(--color-ink-muted);
  opacity: 0;
  transform: translateY(12px);
  transition:
    opacity 0.6s var(--ease-molasses) 0.2s,
    transform 0.6s var(--ease-molasses) 0.2s;
}

.is-ready .home__lead {
  opacity: 1;
  transform: translateY(0);
}

.home__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  opacity: 0;
  transform: translateY(12px);
  transition:
    opacity 0.6s var(--ease-molasses) 0.3s,
    transform 0.6s var(--ease-molasses) 0.3s;
}

.is-ready .home__actions {
  opacity: 1;
  transform: translateY(0);
}

.home__btn {
  display: inline-flex;
  align-items: center;
  padding: 12px 24px;
  border-radius: var(--radius-ui);
  font-size: 15px;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition:
    transform var(--duration-normal) var(--ease-out),
    box-shadow var(--duration-normal) var(--ease-out),
    filter var(--duration-normal) var(--ease-out);
}

.home__btn--primary {
  border: 1px solid rgb(139 105 20 / 0.4);
  background: linear-gradient(180deg, #c4923a 0%, #8b6914 100%);
  color: #fff;
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.25),
    0 1px 3px rgb(20 19 18 / 0.08);
}

.home__btn--primary:hover {
  filter: brightness(1.06);
  transform: translateY(-1px);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.3),
    0 8px 24px var(--color-vu-amber-glow);
}

.home__btn--primary:active {
  transform: translateY(0);
}

.home__btn--ghost {
  border: 1px solid var(--color-line-strong);
  background: var(--color-surface);
  color: var(--color-ink);
}

.home__btn--ghost:hover {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
  transform: translateY(-1px);
}

.home__btn--lg {
  padding: 14px 32px;
  font-size: 16px;
}

/* ---- Section Title ---- */
.home__section-title {
  margin: 0 0 24px;
  font-family: var(--font-scroll);
  font-size: clamp(1.1rem, 2vw, 1.35rem);
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--color-ink);
  display: flex;
  align-items: center;
  gap: 12px;
}

.home__section-title::before {
  content: "";
  display: block;
  width: 24px;
  height: 1px;
  background: var(--color-vu-amber);
  opacity: 0.5;
}

/* ---- 核心工作流速览 ---- */
.home__flow-cards {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.home__flow-card {
  flex: 1;
  min-width: 160px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 24px 22px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-module);
  background: var(--color-surface);
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition:
    border-color var(--duration-slow) var(--ease-out),
    box-shadow var(--duration-slow) var(--ease-out),
    transform var(--duration-slow) var(--ease-out);
}

.home__flow-card:hover {
  border-color: var(--color-vu-amber);
  box-shadow: var(--shadow-lift);
  transform: translateY(-2px);
}

.home__flow-card h3 {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 600;
}

.home__flow-card p {
  margin: 0;
  font-size: 13px;
  color: var(--color-ink-muted);
  line-height: 1.5;
}

.home__flow-num {
  display: flex;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-ui);
  font-family: var(--font-scroll);
  font-size: 16px;
  font-weight: 600;
  color: var(--color-vu-amber-deep);
  background: var(--color-xuan-light);
}

.home__flow-arrow {
  font-family: var(--font-scroll);
  font-size: 20px;
  color: var(--color-brushed-dark);
  flex-shrink: 0;
}

.home__flow-hint {
  margin: 18px 0 0;
  font-size: 13px;
  color: var(--color-ink-muted);
}

.home__flow-hint a {
  color: var(--color-ink);
  text-decoration: underline;
  text-underline-offset: 3px;
}

/* ---- 使用场景 ---- */
.home__scenario-grid {
  display: grid;
  gap: 16px;
}

@media (min-width: 640px) {
  .home__scenario-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 960px) {
  .home__scenario-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.home__scenario-card {
  padding: 24px 22px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-module);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  transition:
    border-color var(--duration-normal) var(--ease-out),
    transform var(--duration-normal) var(--ease-out),
    box-shadow var(--duration-normal) var(--ease-out);
}

.home__scenario-card:hover {
  border-color: var(--color-vu-amber);
  transform: translateY(-2px);
  box-shadow: var(--shadow-lift);
}

.home__scenario-title {
  margin: 0 0 10px;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.4;
}

.home__scenario-desc {
  margin: 0 0 14px;
  font-size: 13px;
  line-height: 1.65;
  color: var(--color-ink-muted);
}

/* ---- FAQ ---- */
.home__faq-list {
  margin: 0;
  display: grid;
  gap: 16px;
}

@media (min-width: 768px) {
  .home__faq-list {
    grid-template-columns: 1fr 1fr;
  }
}

.home__faq-item {
  padding: 20px 22px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-module);
  background: var(--color-xuan-light);
  transition:
    border-color var(--duration-normal) var(--ease-out),
    box-shadow var(--duration-normal) var(--ease-out);
}

.home__faq-item:hover {
  border-color: var(--color-line-strong);
  box-shadow: var(--shadow-card);
}

.home__faq-item dt {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--color-ink);
}

.home__faq-item dd {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--color-ink-muted);
}

/* ---- 底部 CTA ---- */
.home__cta {
  text-align: center;
  padding: 56px 24px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-xl);
  background: linear-gradient(
    170deg,
    var(--color-xuan-light) 0%,
    var(--color-xuan-warm) 60%,
    var(--color-surface) 100%
  );
  box-shadow: var(--shadow-soft);
  position: relative;
  overflow: hidden;
}

.home__cta-title {
  margin: 0 0 12px;
  font-family: var(--font-scroll);
  font-size: clamp(1.25rem, 2.5vw, 1.75rem);
  font-weight: 600;
  letter-spacing: 0.04em;
}

.home__cta-desc {
  margin: 0 0 28px;
  font-size: 15px;
  color: var(--color-ink-muted);
}

/* ── 无障碍 ── */
@media (prefers-reduced-motion: reduce) {
  .home__eyebrow,
  .home__title,
  .home__lead,
  .home__actions {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
</style>
