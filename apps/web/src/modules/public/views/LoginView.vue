<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { healthCheck, login, sendSms } from "@/api/client";
import RackPanel from "@/modules/voice/components/studio/RackPanel.vue";

const router = useRouter();
const route = useRoute();
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
    if (mockCode.value) code.value = mockCode.value;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

function afterAuthEntry() {
  const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "";
  const pick = typeof route.query.pick === "string" ? route.query.pick : "";
  const intent = typeof route.query.intent === "string" ? route.query.intent : "";
  if (redirect.startsWith("/") && redirect !== "/login") {
    if (redirect.includes("?")) {
      router.push(redirect);
    } else {
      const query: Record<string, string> = {};
      if (pick) query.pick = pick;
      if (intent) query.intent = intent;
      router.push(Object.keys(query).length ? { path: redirect, query } : redirect);
    }
  } else {
    router.push("/library");
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
    afterAuthEntry();
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

function enterDevMode() {
  localStorage.removeItem("access_token");
  localStorage.setItem("dev_mode", "1");
  localStorage.setItem("dev_user_id", "00000000-0000-0000-0000-000000000001");
  afterAuthEntry();
}
</script>

<template>
  <div class="login-page">
    <section class="login-page__hero">
      <p class="login-page__eyebrow">Voice Studio</p>
      <h1 class="login-page__title">让文字<br />拥有真实的声音</h1>
      <p class="login-page__lead">
        上传声纹、训练专属音色、一键合成试听。从个人创作到音色交易，完整闭环都在这一个工作台里。
      </p>
      <ul class="login-page__features">
        <li>文本转语音与批量配音</li>
        <li>音色馆上架、购买与授权验真</li>
        <li>合规授权与实名训练门禁</li>
      </ul>
    </section>

    <RackPanel class="login-page__form" title="登录">
      <div class="alert" :class="checking ? 'alert-info' : apiOk ? 'alert-info' : 'alert-error'">
        <template v-if="checking">正在检测平台 API…</template>
        <template v-else-if="apiOk">平台 API 已就绪，可以登录</template>
        <template v-else>
          无法连接 API。请先运行 <code>.\scripts\platform_start.ps1</code> 后再试。
        </template>
      </div>

      <div v-if="!apiOk && !checking" class="row-actions" style="margin-bottom: 16px">
        <a href="/health" target="_blank" rel="noreferrer" class="text-action">检测 /health</a>
        <span class="row-actions__sep" aria-hidden="true">·</span>
        <button type="button" class="text-action" @click="refreshApiStatus">重新检测</button>
      </div>

      <div class="field">
        <label for="phone">手机号</label>
        <input id="phone" v-model="phone" maxlength="11" autocomplete="tel" />
      </div>

      <div class="field" style="margin-top: 16px">
        <label for="code">验证码</label>
        <input id="code" v-model="code" maxlength="6" autocomplete="one-time-code" />
        <p v-if="mockCode" class="field-hint">开发环境验证码：{{ mockCode }}</p>
      </div>

      <div class="row" style="margin-top: 24px">
        <button type="button" class="text-action" :disabled="loading" @click="onSendSms">发送验证码</button>
        <button type="button" class="btn btn-primary btn-lg" :disabled="loading || !apiOk" @click="onLogin">
          进入工作台
        </button>
      </div>

      <div class="login-page__or"><span>或</span></div>

      <button type="button" class="text-action login-page__dev-btn" @click="enterDevMode">
        跳过登录（开发模式）
      </button>

      <p v-if="error" class="alert alert-error" style="margin-top: 16px; margin-bottom: 0">{{ error }}</p>
    </RackPanel>
  </div>
</template>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  gap: 40px;
  padding: 40px 24px;
  align-items: center;
}

@media (min-width: 960px) {
  .login-page {
    grid-template-columns: 1fr minmax(360px, 420px);
    padding: 56px 72px;
  }
}

.login-page__eyebrow {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-brushed-dark);
}

.login-page__title {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(2.25rem, 5vw, 3.25rem);
  font-weight: 600;
  letter-spacing: -0.03em;
  line-height: 1.12;
  color: var(--color-ink);
}

.login-page__lead {
  margin: 20px 0 0;
  max-width: 30rem;
  font-size: 16px;
  line-height: 1.7;
  color: var(--color-ink-muted);
}

.login-page__features {
  margin: 28px 0 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.login-page__features li {
  position: relative;
  padding-left: 22px;
  font-size: 14px;
  color: var(--color-ink-muted);
}

.login-page__features li::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0.55em;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-vu-amber);
  box-shadow: 0 0 0 3px var(--color-vu-amber-soft);
}

.login-page__form {
  width: 100%;
  max-width: 420px;
  justify-self: center;
}

.login-page__or {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 24px 0;
  font-size: 13px;
  color: var(--color-brushed-dark);
}

.login-page__or::before,
.login-page__or::after {
  content: "";
  flex: 1;
  height: 1px;
  background: rgb(212 205 195 / 0.9);
}

.login-page__dev-btn {
  width: 100%;
}
</style>
