<script setup lang="ts">
import { ref, computed } from "vue";
import { useRouter } from "vue-router";
import { useOnboarding, ONBOARDING_STEPS } from "@/composables/useOnboarding";

const router = useRouter();
const { finishOnboarding, skipOnboarding } = useOnboarding();

const currentStep = ref(0);
const totalSteps = ONBOARDING_STEPS.length;

function goStep(step: number) {
  currentStep.value = Math.max(0, Math.min(step, totalSteps - 1));
}

function goRoute(path: string) {
  router.push(path);
  finishOnboarding();
}

defineEmits<{
  close: [];
}>();

/** 步骤图标 SVG path 映射 */
const STEP_ICONS: Record<string, string> = {
  studio: "M12 2a3 3 0 0 0-3 3v3a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z M19 10h-1a7 7 0 0 1-6 6.92V19h3v3H9v-3h3v-2.08A7 7 0 0 1 6 10H5a2 2 0 0 0-2 2v3a2 2 0 0 0 2 2h1a7 7 0 0 0 14 0h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2Z",
  library: "M3 18v-6a9 9 0 0 1 18 0v6 M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z",
  catalog: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20 M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z M9 7h6 M9 11h6 M9 15h4",
  community: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z M23 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75",
};

const currentIcon = computed(() => STEP_ICONS[ONBOARDING_STEPS[currentStep.value]?.icon] ?? "");
</script>

<template>
  <Teleport to="body">
    <div class="onboard-overlay" @click.self="$emit('close')">
      <div class="onboard-dialog">
        <button class="onboard-dialog__close" aria-label="关闭" @click="$emit('close')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>

        <div class="onboard-dialog__body">
          <div class="onboard-dialog__brand">
            <span class="onboard-dialog__brand-icon" aria-hidden="true">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M2 10v4 M6 8v8 M10 5v14 M14 9v6 M18 7v10 M22 11v2" />
              </svg>
            </span>
            <div>
              <p class="onboard-dialog__brand-name">欢迎来到 Phonia</p>
              <p class="onboard-dialog__brand-sub">AI 声纹克隆与配音平台</p>
            </div>
          </div>

          <div class="onboard-steps">
            <div class="onboard-steps__indicator">
              <button
                v-for="(step, i) in ONBOARDING_STEPS"
                :key="step.id"
                class="onboard-steps__dot"
                :class="{
                  'onboard-steps__dot--on': i === currentStep,
                  'onboard-steps__dot--done': i < currentStep,
                }"
                :aria-label="`步骤 ${i + 1}: ${step.title}`"
                @click="goStep(i)"
              />
            </div>

            <div class="onboard-steps__card">
              <span class="onboard-steps__icon" aria-hidden="true">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">
                  <path :d="currentIcon" />
                </svg>
              </span>
              <div class="onboard-steps__text">
                <span class="onboard-steps__num">第 {{ currentStep + 1 }}/{{ totalSteps }} 步</span>
                <h3 class="onboard-steps__title">{{ ONBOARDING_STEPS[currentStep].title }}</h3>
                <p class="onboard-steps__desc">{{ ONBOARDING_STEPS[currentStep].desc }}</p>
              </div>
            </div>
          </div>

          <div class="onboard-dialog__actions">
            <div class="onboard-dialog__nav">
              <button
                class="onboard-dialog__btn onboard-dialog__btn--ghost"
                :disabled="currentStep === 0"
                @click="goStep(currentStep - 1)"
              >
                上一步
              </button>
              <button
                v-if="currentStep < totalSteps - 1"
                class="onboard-dialog__btn onboard-dialog__btn--primary"
                @click="goStep(currentStep + 1)"
              >
                继续
              </button>
              <button
                v-else
                class="onboard-dialog__btn onboard-dialog__btn--primary"
                @click="goRoute(ONBOARDING_STEPS[currentStep].route)"
              >
                {{ ONBOARDING_STEPS[currentStep].routeLabel }}
              </button>
            </div>
            <div class="onboard-dialog__skip">
              <button class="onboard-dialog__btn onboard-dialog__btn--text" @click="skipOnboarding">
                稍后再说
              </button>
              <button class="onboard-dialog__btn onboard-dialog__btn--text" @click="finishOnboarding">
                跳过引导
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.onboard-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(31 28 25 / 0.45);
  backdrop-filter: blur(4px);
  animation: onboard-fade-in 0.2s var(--ease-out);
}

@keyframes onboard-fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.onboard-dialog {
  position: relative;
  width: min(640px, 94vw);
  max-height: 92vh;
  overflow-y: auto;
  background: var(--color-surface);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-lg);
  box-shadow:
    0 24px 72px rgb(31 28 25 / 0.15),
    0 10px 30px rgb(31 28 25 / 0.08);
  animation: onboard-slide-up 0.3s var(--ease-spring);
}

@keyframes onboard-slide-up {
  from {
    opacity: 0;
    transform: translateY(24px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.onboard-dialog__close {
  position: absolute;
  top: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: var(--radius-ui);
  background: transparent;
  color: var(--color-ink-muted);
  cursor: pointer;
}

.onboard-dialog__close:hover {
  background: rgb(31 28 25 / 0.04);
  color: var(--color-ink);
}

.onboard-dialog__body {
  padding: 40px 40px 36px;
}

.onboard-dialog__brand {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 36px;
}

.onboard-dialog__brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  flex-shrink: 0;
  border-radius: 10px;
  background: linear-gradient(150deg, var(--color-highlight) 0%, var(--color-vu-amber) 100%);
  font-family: var(--font-display);
  font-size: 20px;
  color: #fff;
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.3),
    0 4px 18px var(--color-vu-amber-glow);
}

.onboard-dialog__brand-name {
  margin: 0;
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.onboard-dialog__brand-sub {
  margin: 3px 0 0;
  font-size: 14px;
  color: var(--color-ink-muted);
}

.onboard-steps {
  margin-bottom: 32px;
}

.onboard-steps__indicator {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: 24px;
}

.onboard-steps__dot {
  width: 10px;
  height: 10px;
  border: none;
  border-radius: 999px;
  background: var(--color-line-strong);
  cursor: pointer;
  padding: 0;
  transition:
    background var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
}

.onboard-steps__dot--on {
  background: var(--color-vu-amber);
  transform: scale(1.35);
}

.onboard-steps__dot--done {
  background: var(--color-brushed);
}

.onboard-steps__card {
  display: flex;
  gap: 18px;
  padding: 28px;
  border: 1px solid var(--color-line);
  border-radius: var(--radius-module);
  background: var(--color-xuan-light);
}

.onboard-steps__icon {
  display: flex;
  align-items: flex-start;
  flex-shrink: 0;
  color: var(--theme-warm);
  padding-top: 2px;
}

.onboard-steps__text {
  min-width: 0;
}

.onboard-steps__num {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-brushed-dark);
}

.onboard-steps__title {
  margin: 6px 0 10px;
  font-size: 20px;
  font-weight: 600;
}

.onboard-steps__desc {
  margin: 0;
  font-size: 15px;
  line-height: 1.7;
  color: var(--color-ink-muted);
}

.onboard-dialog__actions {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.onboard-dialog__nav {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.onboard-dialog__skip {
  display: flex;
  justify-content: center;
  gap: 24px;
}

.onboard-dialog__btn {
  padding: 12px 28px;
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-ui);
  background: var(--color-surface);
  font-size: 15px;
  font-weight: 500;
  color: var(--color-ink);
  cursor: pointer;
  white-space: nowrap;
}

.onboard-dialog__btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.onboard-dialog__btn--primary {
  border-color: var(--color-vu-amber);
  background: linear-gradient(135deg, var(--color-highlight), var(--color-vu-amber));
  color: #fff;
  box-shadow: 0 2px 12px var(--color-vu-amber-glow);
}

.onboard-dialog__btn--primary:hover {
  filter: brightness(1.1);
}

.onboard-dialog__btn--ghost {
  border-color: transparent;
  background: transparent;
  color: var(--color-ink-muted);
}

.onboard-dialog__btn--ghost:hover:not(:disabled) {
  color: var(--color-ink);
  background: rgb(255 255 255 / 0.05);
}

.onboard-dialog__btn--text {
  border: none;
  background: none;
  padding: 8px 14px;
  font-size: 13px;
  color: var(--color-brushed-dark);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.onboard-dialog__btn--text:hover {
  color: var(--color-ink-muted);
}
</style>
