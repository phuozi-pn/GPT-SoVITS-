/**
 * 新手引导状态管理
 *
 * 功能：
 * - 检测是否为新用户（首次登录）
 * - 记录已完成的引导步骤
 * - 控制欢迎弹窗和功能导览的显示
 */

import { ref, computed, onMounted } from "vue";

const STORAGE_KEY = "onboarding_completed";
const FIRST_LOGIN_KEY = "first_login_at";

export type OnboardingStep = {
  id: string;
  title: string;
  desc: string;
  route: string;
  routeLabel: string;
  icon: string; // emoji 或简标
};

/** 新手指南步骤 */
export const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    id: "train",
    title: "训练你的第一个音色",
    desc: "上传授权干声，AI 克隆声纹，这是所有配音的起点。训练前需要先完成实名认证。",
    route: "/studio",
    routeLabel: "去训练工作台",
    icon: "studio",
  },
  {
    id: "synth",
    title: "尝试智能配音",
    desc: "选一个音色，输入文本或粘贴剧本，AI 自动生成语音。支持单人朗读、多人对话、歌曲念唱。",
    route: "/library",
    routeLabel: "去智能配音",
    icon: "library",
  },
  {
    id: "browse",
    title: "逛逛音色馆",
    desc: "浏览公开上架的音色，试听样音，购买授权后可直接使用，无需自己训练。",
    route: "/catalog",
    routeLabel: "去音色馆",
    icon: "catalog",
  },
  {
    id: "community",
    title: "加入社区",
    desc: "发现创作者、点赞动态、发帖交流，或给心仪的创作者发私信洽谈授权。",
    route: "/discover/feed",
    routeLabel: "去社区动态",
    icon: "community",
  },
];

// 模块级单例状态 — 所有调用者共享同一份响应式状态
const completed = ref(false);
const firstLoginAt = ref<string | null>(null);
const showWelcome = ref(false);
const currentStep = ref(0);

let initialized = false;

export function useOnboarding() {
  const isNewUser = computed(() => !completed.value);

  /** 初始化：从 localStorage 读取状态 */
  function init() {
    if (initialized) return;
    initialized = true;

    completed.value = localStorage.getItem(STORAGE_KEY) === "1";
    firstLoginAt.value = localStorage.getItem(FIRST_LOGIN_KEY);

    // 登录后但未完成引导 → 显示欢迎
    const hasSession = !!localStorage.getItem("access_token") || localStorage.getItem("dev_mode") === "1";
    if (hasSession && !completed.value) {
      showWelcome.value = true;
    }
  }

  /** 记录首次登录时间 */
  function recordFirstLogin() {
    if (!localStorage.getItem(FIRST_LOGIN_KEY)) {
      localStorage.setItem(FIRST_LOGIN_KEY, new Date().toISOString());
    }
  }

  /** 完成引导 */
  function finishOnboarding() {
    completed.value = true;
    showWelcome.value = false;
    localStorage.setItem(STORAGE_KEY, "1");
  }

  /** 跳过引导（之后仍可触发） */
  function skipOnboarding() {
    showWelcome.value = false;
  }

  /** 重新开启引导（用户主动触发） */
  function restartOnboarding() {
    showWelcome.value = true;
    currentStep.value = 0;
  }

  /** 关闭欢迎弹窗 */
  function closeWelcome() {
    showWelcome.value = false;
  }

  // 自动初始化
  onMounted(init);

  return {
    completed,
    firstLoginAt,
    showWelcome,
    currentStep,
    isNewUser,
    init,
    recordFirstLogin,
    finishOnboarding,
    skipOnboarding,
    restartOnboarding,
    closeWelcome,
  };
}
