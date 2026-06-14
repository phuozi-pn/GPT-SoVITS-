<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { healthCheck, login, sendSms } from "@/api/client";

const router = useRouter();
const phone = ref("13800000001");
const code = ref("");
const mockCode = ref<string | null>(null);
const loading = ref(false);
const error = ref("");
const apiOk = ref(false);
const checking = ref(true);
let pollTimer: ReturnType<typeof setInterval> | null = null;

async function refreshApiStatus() {
  checking.value = true;
  apiOk.value = await healthCheck();
  checking.value = false;
}

onMounted(async () => {
  await refreshApiStatus();
  pollTimer = setInterval(refreshApiStatus, 5000);
});

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer);
});

async function onSendSms() {
  error.value = "";
  loading.value = true;
  try {
    const res = await sendSms(phone.value.trim());
    mockCode.value = res.mock_code ?? null;
    if (mockCode.value) {
      code.value = mockCode.value;
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

async function onLogin() {
  error.value = "";
  loading.value = true;
  try {
    const res = await login(phone.value.trim(), code.value.trim());
    localStorage.setItem("access_token", res.access_token);
    localStorage.removeItem("dev_mode");
    localStorage.setItem("user_phone", res.user.phone);
    router.push("/studio");
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

function enterDevMode() {
  localStorage.removeItem("access_token");
  localStorage.setItem("dev_mode", "1");
  router.push("/studio");
}
</script>

<template>
  <div class="login-page">
    <div class="login-brand">
      <div class="login-brand__inner">
        <p class="login-brand__eyebrow">MVP-0 · GPT-SoVITS</p>
        <h1>AI 配音<br />音色工作台</h1>
        <p class="login-brand__lead">
          上传干声 → 训练专属音色 → 文本合成试听。适用于短剧旁白与多角色配音流程验证。
        </p>
        <ul class="login-brand__features">
          <li>声纹授权与素材质检</li>
          <li>GPU 任务队列与配额</li>
          <li>合规 AI 生成告知</li>
        </ul>
      </div>
    </div>

    <div class="login-form-wrap">
      <div class="login-card card">
        <h2 class="card__title">登录账号</h2>
        <p class="card__desc">使用手机号验证码进入工作台</p>

        <div
          class="alert"
          :class="checking ? 'alert--info' : apiOk ? 'alert--info' : 'alert--error'"
        >
          <span aria-hidden="true">{{ apiOk ? "✓" : "!" }}</span>
          <div>
            <template v-if="checking">正在检测 API 连接…</template>
            <template v-else-if="apiOk">平台 API 已就绪（默认 :8001）</template>
            <template v-else>
              请先启动后端：<code>.\scripts\platform_start.ps1</code>，并确保 Docker 中 PG/Redis 已运行。
            </template>
          </div>
        </div>

        <div v-if="!apiOk && !checking" class="row" style="margin-bottom: 1rem">
          <a href="/health" target="_blank" rel="noreferrer" class="btn btn--ghost btn--sm">打开 /health</a>
          <button type="button" class="btn btn--ghost btn--sm" @click="refreshApiStatus">重新检测</button>
        </div>

        <div class="field">
          <label for="phone">手机号</label>
          <input id="phone" v-model="phone" maxlength="11" placeholder="13800000001" autocomplete="tel" />
        </div>

        <div class="field">
          <label for="code">验证码</label>
          <input id="code" v-model="code" maxlength="6" placeholder="6 位数字" autocomplete="one-time-code" />
          <p v-if="mockCode" class="field-hint status warn">开发环境验证码：{{ mockCode }}</p>
        </div>

        <div class="row">
          <button type="button" class="btn btn--ghost" :disabled="loading" @click="onSendSms">发送验证码</button>
          <button type="button" class="btn btn--primary btn--lg" :disabled="loading || !apiOk" @click="onLogin">
            进入工作台
          </button>
        </div>

        <div class="login-divider"><span>或</span></div>

        <button type="button" class="btn btn--ghost" style="width: 100%" @click="enterDevMode">
          跳过登录（DEV_SKIP_AUTH）
        </button>

        <p v-if="error" class="alert alert--error" style="margin-top: 1rem; margin-bottom: 0">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: grid;
  grid-template-columns: 1fr;
  min-height: calc(100vh - 0px);
  width: 100%;
}

@media (min-width: 880px) {
  .login-page {
    grid-template-columns: 1fr 1fr;
  }
}

.login-brand {
  display: none;
  color: #fff;
  padding: 3rem 2.5rem;
  align-items: center;
}

@media (min-width: 880px) {
  .login-brand {
    display: flex;
  }
}

.login-brand__inner {
  max-width: 400px;
}

.login-brand__eyebrow {
  margin: 0 0 1rem;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.7;
}

.login-brand h1 {
  margin: 0 0 1rem;
  font-size: 2.25rem;
  font-weight: 800;
  line-height: 1.15;
  letter-spacing: -0.03em;
}

.login-brand__lead {
  margin: 0 0 1.5rem;
  font-size: 1rem;
  line-height: 1.6;
  opacity: 0.85;
}

.login-brand__features {
  margin: 0;
  padding: 0;
  list-style: none;
}

.login-brand__features li {
  position: relative;
  padding-left: 1.35rem;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  opacity: 0.8;
}

.login-brand__features li::before {
  content: "✓";
  position: absolute;
  left: 0;
  color: #5eead4;
  font-weight: 700;
}

.login-form-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1.25rem;
  background: var(--bg);
}

@media (min-width: 880px) {
  .login-form-wrap {
    background: var(--surface);
  }
}

.login-card {
  width: 100%;
  max-width: 420px;
  box-shadow: var(--shadow-lg);
}

.login-divider {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 1.25rem 0;
  color: var(--text-muted);
  font-size: 0.8rem;
}

.login-divider::before,
.login-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: var(--border);
}

code {
  font-size: 0.8em;
  background: rgba(0, 0, 0, 0.06);
  padding: 0.1em 0.35em;
  border-radius: 4px;
}
</style>
