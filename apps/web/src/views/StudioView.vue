<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  ApiError,
  confirmAsset,
  createConsent,
  createVoice,
  fetchQuota,
  pollJob,
  startTrain,
  synthesize,
  uploadAsset,
  type QuotaSummary,
} from "@/api/client";

const router = useRouter();
const devMode = ref(localStorage.getItem("dev_mode") === "1");
const quota = ref<QuotaSummary | null>(null);

const voiceName = ref("我的音色");
const voiceId = ref("");
const assetId = ref("");
const voiceVersionId = ref("");
const refText = ref("大家好，我是测试用户，今天我们来测试一下语音合成功能。");
const synthText = ref("你好，这是一次语音合成测试。");
const audioFile = ref<File | null>(null);
const audioUrl = ref("");
const fileInputRef = ref<HTMLInputElement | null>(null);

const step = ref(1);
const busy = ref(false);
const busyLabel = ref("处理中…");
const error = ref("");
const logLines = ref<string[]>([]);

const steps = [
  { n: 1, label: "创建音色", desc: "命名并提交声纹授权" },
  { n: 2, label: "上传素材", desc: "约 8–10 分钟干声" },
  { n: 3, label: "训练", desc: "GPU 微调任务" },
  { n: 4, label: "合成试听", desc: "输入文本生成语音" },
];

function pushLog(line: string) {
  logLines.value.push(`[${new Date().toLocaleTimeString()}] ${line}`);
}

onMounted(async () => {
  try {
    quota.value = await fetchQuota();
  } catch {
    /* dev mode without login may still work with DEV_SKIP_AUTH */
  }
});

function stepItemClass(n: number) {
  if (n < step.value) return "stepper__item is-done";
  if (n === step.value) return "stepper__item is-active";
  return "stepper__item";
}

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  audioFile.value = input.files?.[0] ?? null;
}

function pickFile() {
  fileInputRef.value?.click();
}

async function runStep1() {
  error.value = "";
  busy.value = true;
  busyLabel.value = "创建音色…";
  try {
    const v = await createVoice(voiceName.value.trim());
    voiceId.value = v.voice_id;
    pushLog(`音色已创建 ${v.voice_id}`);
    const c = await createConsent(voiceId.value);
    pushLog(`授权 ${c.status} consent=${c.consent_id}`);
    step.value = 2;
  } catch (e) {
    error.value = formatError(e);
  } finally {
    busy.value = false;
  }
}

async function runStep2() {
  if (!voiceId.value) {
    error.value = "请先创建音色";
    return;
  }
  if (!audioFile.value) {
    error.value = "请选择 wav 文件";
    return;
  }
  if (!refText.value.trim()) {
    error.value = "请填写参考文本（与音频内容一致）";
    return;
  }
  error.value = "";
  busy.value = true;
  busyLabel.value = "上传并质检…";
  try {
    const up = await uploadAsset(voiceId.value, refText.value.trim(), audioFile.value);
    assetId.value = up.asset_id;
    pushLog(`上传 asset=${up.asset_id} qc=${up.qc_passed}`);
    if (!up.qc_passed) {
      const issues = up.qc_result?.issues?.map((i) => i.message).join("; ") ?? "质检未通过";
      throw new Error(issues);
    }
    await confirmAsset(assetId.value);
    pushLog("素材已锁定");
    step.value = 3;
  } catch (e) {
    error.value = formatError(e);
  } finally {
    busy.value = false;
  }
}

async function runStep3() {
  if (!voiceId.value || !assetId.value) {
    error.value = "请先完成上传";
    return;
  }
  error.value = "";
  busy.value = true;
  busyLabel.value = "训练进行中…";
  try {
    const t = await startTrain(voiceId.value, assetId.value);
    pushLog(`训练 job=${t.job_id} 排队中…`);
    const job = await pollJob(t.job_id, (j) => pushLog(`训练状态 ${j.status}`));
    if (job.status !== "succeeded" || !job.voice_version_id) {
      throw new Error(job.error_message ?? "训练失败");
    }
    voiceVersionId.value = job.voice_version_id;
    pushLog(`训练完成 version=${voiceVersionId.value}`);
    step.value = 4;
    quota.value = await fetchQuota().catch(() => quota.value);
  } catch (e) {
    error.value = formatError(e);
  } finally {
    busy.value = false;
  }
}

async function runStep4() {
  if (!voiceVersionId.value) {
    error.value = "请先完成训练";
    return;
  }
  if (!synthText.value.trim()) {
    error.value = "请输入要合成的文本";
    return;
  }
  error.value = "";
  busy.value = true;
  busyLabel.value = "合成中…";
  audioUrl.value = "";
  try {
    const s = await synthesize(voiceVersionId.value, synthText.value.trim());
    pushLog(`合成 job=${s.job_id}`);
    const job = await pollJob(s.job_id, (j) => pushLog(`合成 ${j.status}`), 120_000);
    if (job.status !== "succeeded" || !job.audio_url) {
      throw new Error(job.error_message ?? "合成失败");
    }
    audioUrl.value = job.audio_url;
    pushLog(`合成完成 ${job.audio_url}`);
    quota.value = await fetchQuota().catch(() => quota.value);
  } catch (e) {
    error.value = formatError(e);
  } finally {
    busy.value = false;
  }
}

function formatError(e: unknown): string {
  if (e instanceof ApiError) return `${e.code}: ${e.message}`;
  if (e instanceof Error) return e.message;
  return String(e);
}

function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("dev_mode");
  router.push("/login");
}

function goBack() {
  if (step.value > 1 && !busy.value) step.value -= 1;
}

const charPercent = computed(() => {
  if (!quota.value) return 0;
  return Math.min(100, (quota.value.chars_used / quota.value.monthly_char_limit) * 100);
});

const trainPercent = computed(() => {
  if (!quota.value) return 0;
  return Math.min(100, (quota.value.trainings_used / quota.value.monthly_train_limit) * 100);
});

const logText = computed(() => logLines.value.join("\n") || "");
</script>

<template>
  <div>
    <div v-if="busy" class="busy-overlay" aria-live="polite">
      <div class="busy-overlay__box">
        <div class="spinner" />
        <p>{{ busyLabel }}</p>
      </div>
    </div>

    <header class="page-hero row" style="justify-content: space-between; align-items: flex-start">
      <div>
        <h1>配音工作台</h1>
        <p>四步完成：授权 → 素材 → 训练 → 合成</p>
      </div>
      <button type="button" class="btn btn--ghost btn--sm" @click="logout">退出</button>
    </header>

    <div v-if="quota" class="card" style="margin-bottom: 1.25rem">
      <div class="quota-grid">
        <div class="quota-meter">
          <div class="quota-meter__label">本月合成字符</div>
          <div class="quota-meter__value">
            {{ quota.chars_used.toLocaleString() }} / {{ quota.monthly_char_limit.toLocaleString() }}
          </div>
          <div class="quota-meter__bar">
            <div class="quota-meter__fill" :style="{ width: charPercent + '%' }" />
          </div>
        </div>
        <div class="quota-meter">
          <div class="quota-meter__label">本月训练次数</div>
          <div class="quota-meter__value">
            {{ quota.trainings_used }} / {{ quota.monthly_train_limit }}
          </div>
          <div class="quota-meter__bar">
            <div class="quota-meter__fill" :style="{ width: trainPercent + '%' }" />
          </div>
        </div>
      </div>
    </div>

    <ol class="stepper" aria-label="工作流步骤">
      <li v-for="s in steps" :key="s.n" :class="stepItemClass(s.n)">
        <span class="stepper__dot">{{ s.n < step ? "✓" : s.n }}</span>
        <span class="stepper__label">{{ s.label }}</span>
      </li>
    </ol>

    <div class="studio-grid">
      <div class="studio-main">
        <div v-if="error" class="alert alert--error">{{ error }}</div>

        <!-- Step 1 -->
        <div v-show="step === 1" class="card">
          <h2 class="card__title">创建音色</h2>
          <p class="card__desc">为本次克隆命名，系统将自动创建声纹授权记录（MVP 可自动通过）。</p>
          <div class="field">
            <label for="voiceName">音色名称</label>
            <input id="voiceName" v-model="voiceName" placeholder="例如：旁白男声-001" />
          </div>
          <div class="alert alert--compliance">
            请仅上传<strong>本人或已获授权</strong>的声纹素材，禁止未授权仿名人/他人声音。
          </div>
          <button type="button" class="btn btn--primary btn--lg" :disabled="busy" @click="runStep1">
            创建并提交授权
          </button>
        </div>

        <!-- Step 2 -->
        <div v-show="step === 2" class="card">
          <h2 class="card__title">上传训练素材</h2>
          <p class="card__desc">上传 8–10 分钟干声 wav，参考文本需与音频内容一致。</p>
          <p v-if="voiceId" class="meta-chip" style="margin-bottom: 1rem">voice_id: {{ voiceId }}</p>

          <div class="field">
            <label for="refText">参考文本</label>
            <textarea id="refText" v-model="refText" placeholder="与 wav 朗读内容一致…" />
            <p class="field-hint">用于质检与训练对齐，请尽量准确。</p>
          </div>

          <div class="field">
            <label>音频文件</label>
            <div
              class="upload-zone"
              :class="{ 'has-file': !!audioFile }"
              role="button"
              tabindex="0"
              @click="pickFile"
              @keydown.enter="pickFile"
            >
              <div class="upload-zone__icon">📁</div>
              <p v-if="audioFile" class="upload-zone__name">{{ audioFile.name }}</p>
              <p v-else>点击选择 .wav 文件</p>
              <p class="field-hint">建议：单声道、无 BGM、8–10 分钟</p>
              <input ref="fileInputRef" type="file" accept=".wav,audio/wav" @change="onFileChange" />
            </div>
          </div>

          <div class="alert alert--warn">
            短样本测试请在 .env 设置 <code>QC_DEV_RELAX_DURATION=true</code>；生产素材需满足时长质检。
          </div>

          <div class="row">
            <button type="button" class="btn btn--ghost" :disabled="busy" @click="goBack">上一步</button>
            <button type="button" class="btn btn--primary btn--lg" :disabled="busy" @click="runStep2">
              上传、质检并锁定
            </button>
          </div>
        </div>

        <!-- Step 3 -->
        <div v-show="step === 3" class="card">
          <h2 class="card__title">训练音色</h2>
          <p class="card__desc">提交 GPU 微调任务，完成后获得可合成的 voice_version。</p>
          <p v-if="assetId" class="meta-chip" style="margin-bottom: 1rem">asset_id: {{ assetId }}</p>

          <div class="alert alert--info">
            <div>
              <strong>训练模式说明</strong><br />
              默认 <code>TRAIN_MOCK=true</code> 为占位训练；真微调请在云端 GPU 完成后再接入平台，或配置
              <code>ENGINE_TRAIN_*</code>。
            </div>
          </div>

          <div class="row">
            <button type="button" class="btn btn--ghost" :disabled="busy" @click="goBack">上一步</button>
            <button type="button" class="btn btn--primary btn--lg" :disabled="busy" @click="runStep3">
              开始训练
            </button>
          </div>
        </div>

        <!-- Step 4 -->
        <div v-show="step === 4" class="card">
          <h2 class="card__title">合成试听</h2>
          <p class="card__desc">输入文本，使用训练好的音色生成语音。</p>
          <p v-if="voiceVersionId" class="meta-chip" style="margin-bottom: 1rem">
            version: {{ voiceVersionId }}
          </p>

          <div class="field">
            <label for="synthText">合成文本</label>
            <textarea id="synthText" v-model="synthText" placeholder="输入要朗读的内容…" />
          </div>

          <div class="alert alert--compliance">
            ⚠ 本内容由 <strong>AI 生成</strong>，属于深度合成语音。对外发布请遵守标识与授权要求。
          </div>

          <button type="button" class="btn btn--primary btn--lg" :disabled="busy" @click="runStep4">
            开始合成
          </button>

          <div v-if="audioUrl" class="audio-player">
            <strong>试听结果</strong>
            <audio :src="audioUrl" controls autoplay />
          </div>
        </div>
      </div>

      <aside class="studio-sidebar">
        <div class="card">
          <h2 class="card__title" style="font-size: 1rem">操作日志</h2>
          <p class="card__desc" style="margin-bottom: 0.75rem">任务状态与 API 回调记录</p>
          <div class="log-panel">{{ logText }}</div>
        </div>

        <div class="card">
          <h2 class="card__title" style="font-size: 1rem">当前进度</h2>
          <ul class="progress-list">
            <li :class="{ done: step > 1 }">音色 ID {{ voiceId ? "✓" : "—" }}</li>
            <li :class="{ done: step > 2 }">素材锁定 {{ assetId ? "✓" : "—" }}</li>
            <li :class="{ done: step > 3 }">训练版本 {{ voiceVersionId ? "✓" : "—" }}</li>
            <li :class="{ done: !!audioUrl }">合成试听 {{ audioUrl ? "✓" : "—" }}</li>
          </ul>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.progress-list {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 0.875rem;
}

.progress-list li {
  padding: 0.45rem 0;
  border-bottom: 1px solid var(--border);
  color: var(--text-muted);
}

.progress-list li:last-child {
  border-bottom: none;
}

.progress-list li.done {
  color: var(--ok);
  font-weight: 600;
}

code {
  font-size: 0.85em;
  background: rgba(0, 0, 0, 0.05);
  padding: 0.1em 0.35em;
  border-radius: 4px;
}
</style>
