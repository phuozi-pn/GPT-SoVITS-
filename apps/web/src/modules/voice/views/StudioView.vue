<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { fetchKycStatus } from "@/api/kyc";
import {
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
import MakeWorkspace from "@/modules/produce/components/MakeWorkspace.vue";
import ErrorBanner from "@/components/ErrorBanner.vue";
import HelpHint from "@/components/HelpHint.vue";
import PageHero from "@/components/PageHero.vue";
import PageSurface from "@/components/PageSurface.vue";
import StepTabs from "@/components/StepTabs.vue";
import RackPanel from "@/modules/voice/components/studio/RackPanel.vue";
import TapeReel from "@/modules/voice/components/studio/TapeReel.vue";
import { useWorkspaceShell } from "@/composables/useWorkspaceShell";
import { PAGE_META } from "@/config/navigation";
import { formatApiError } from "@/utils/apiErrors";
import { buildSynthesisPayload, newSegment } from "@/modules/produce/types/script";

const router = useRouter();
const { devMode } = useWorkspaceShell();
const studioMeta = PAGE_META.studio;
const quota = ref<QuotaSummary | null>(null);

const voiceName = ref("我的音色");
const voiceId = ref("");
const assetId = ref("");
const voiceVersionId = ref("");
const refText = ref("大家好，我是测试用户，今天我们来测试一下语音合成功能。");
const segments = ref([newSegment("", "你好，这是一次语音合成测试。")]);
const multiMode = ref(false);
const speed = ref(1.05);
const temperature = ref(0.78);
const aiAck = ref(true);
const audioFile = ref<File | null>(null);
const audioUrl = ref("");
const fileInputRef = ref<HTMLInputElement | null>(null);

const step = ref(1);
const busy = ref(false);
const busyLabel = ref("处理中…");
const error = ref("");
const logLines = ref<string[]>([]);
const kycVerified = ref<boolean | null>(null);
const kycBlocked = computed(() => kycVerified.value === false);

const steps = [
  { n: 1, label: "创建音色", desc: "命名并提交声纹授权" },
  { n: 2, label: "上传素材", desc: "约 8–10 分钟干声" },
  { n: 3, label: "训练", desc: "GPU 微调任务" },
  { n: 4, label: "合成试听", desc: "输入文本生成语音" },
];

const studioVoices = computed(() =>
  voiceVersionId.value
    ? [
        {
          id: voiceVersionId.value,
          title: voiceName.value || "训练音色",
          subtitle: voiceVersionId.value.slice(0, 12) + "…",
        },
      ]
    : [],
);

const pipeline = computed(() => [
  { key: "voice", label: "音色", done: !!voiceId.value, active: step.value === 1 },
  { key: "asset", label: "素材", done: !!assetId.value, active: step.value === 2 },
  { key: "train", label: "训练", done: !!voiceVersionId.value, active: step.value === 3 },
  { key: "synth", label: "试听", done: !!audioUrl.value, active: step.value === 4 },
]);

function pushLog(line: string) {
  logLines.value.push(`[${new Date().toLocaleTimeString()}] ${line}`);
}

onMounted(async () => {
  try {
    quota.value = await fetchQuota();
  } catch {
    /* dev mode */
  }
  try {
    const kyc = await fetchKycStatus();
    kycVerified.value = kyc.verified;
  } catch {
    kycVerified.value = null;
  }
});

watch(voiceVersionId, (id) => {
  if (!id) return;
  segments.value = segments.value.map((s) => ({ ...s, voiceVersionId: id }));
});

function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  audioFile.value = input.files?.[0] ?? null;
}

function pickFile() {
  fileInputRef.value?.click();
}

async function runStep1() {
  if (kycBlocked.value) {
    error.value = "请先完成实名认证后再创建音色。";
    return;
  }
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
    error.value = formatApiError(e);
  } finally {
    busy.value = false;
  }
}

async function runStep2() {
  if (!voiceId.value) {
    error.value = "请先创建音色——完成步骤 ① 后再上传素材";
    return;
  }
  if (!audioFile.value) {
    error.value = "还没有选择音频——点击上传区选择 .wav 文件";
    return;
  }
  if (!refText.value.trim()) {
    error.value = "请填写参考文本（需与 wav 朗读内容一致）";
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
    error.value = formatApiError(e);
  } finally {
    busy.value = false;
  }
}

async function runStep3() {
  if (!voiceId.value || !assetId.value) {
    error.value = "请先完成上传——返回步骤 ② 选择并锁定素材";
    return;
  }
  if (kycVerified.value === false) {
    error.value = "请先完成实名认证后再训练";
    router.push("/kyc");
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
      throw new Error(job.error_message ?? "训练失败——请查看日志或确认 TRAIN_MOCK / GPU 配置");
    }
    voiceVersionId.value = job.voice_version_id;
    pushLog(`训练完成 version=${voiceVersionId.value}`);
    step.value = 4;
    quota.value = await fetchQuota().catch(() => quota.value);
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    busy.value = false;
  }
}

async function runStep4() {
  if (!voiceVersionId.value) {
    error.value = "请先完成训练——步骤 ③ 成功后再合成试听";
    return;
  }
  error.value = "";
  busy.value = true;
  busyLabel.value = "合成中…";
  audioUrl.value = "";
  try {
    const payload = buildSynthesisPayload(segments.value, {
      speed: speed.value,
      temperature: temperature.value,
      emotion: null,
      emotionStrength: 0.5,
    });
    const s = await synthesize(payload, aiAck.value);
    pushLog(`合成 job=${s.job_id}`);
    const job = await pollJob(s.job_id, (j) => pushLog(`合成 ${j.status}`), 120_000);
    if (job.status !== "succeeded" || !job.audio_url) {
      throw new Error(job.error_message ?? "合成失败——请确认 infer worker 与引擎是否在运行");
    }
    audioUrl.value = job.audio_url;
    pushLog(`合成完成 ${job.audio_url}`);
    quota.value = await fetchQuota().catch(() => quota.value);
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    busy.value = false;
  }
}

function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("dev_mode");
  router.push("/login");
}

function goBack() {
  if (step.value > 1 && !busy.value) step.value -= 1;
}

function onStepSelect(n: number) {
  if (busy.value) return;
  if (n <= step.value) step.value = n;
}

const logText = computed(() => logLines.value.join("\n") || "还没有操作记录——完成各步骤后会显示在这里");
</script>

<template>
  <div class="page page--fill">
    <div v-if="busy" class="busy-overlay" aria-live="polite">
      <div class="busy-overlay__box rack-panel">
        <span v-for="n in 4" :key="n" class="rack-screw" :class="`rack-screw--${['tl', 'tr', 'bl', 'br'][n - 1]}`" aria-hidden="true" />
        <TapeReel :spinning="true" :size="72" />
        <p class="rack-title" style="margin: 16px 0 4px">{{ busyLabel }}</p>
        <p class="hint">磁带转动中，请勿关闭页面</p>
      </div>
    </div>

    <PageSurface>
      <PageHero compact flow title="训练工作台" :hint="studioMeta.desc">
      <template #stats>
        <p class="page-metrics">
          <template v-if="quota">
            合成字符 <strong>{{ quota.chars_used.toLocaleString() }}/{{ quota.monthly_char_limit.toLocaleString() }}</strong>
            · 训练 <strong>{{ quota.trainings_used }}/{{ quota.monthly_train_limit }}</strong>
            ·
          </template>
          步骤 <strong class="page-metrics__accent">{{ step }}/4</strong>
        </p>
      </template>
      <template #actions>
        <div class="hero-actions">
          <router-link v-if="voiceVersionId" :to="`/quality/${voiceVersionId}`" class="text-action">AB 测评</router-link>
          <button type="button" class="text-action text-action--danger" @click="logout">退出</button>
        </div>
      </template>
      </PageHero>

      <div v-if="kycVerified === false" class="alert alert--warn studio-kyc">
        训练自有声纹前需完成<strong>实名认证</strong>。
        <router-link to="/kyc" class="text-action">去认证</router-link>
      </div>
      <p v-else-if="kycVerified === null" class="hint studio-kyc-hint">正在检查实名状态…</p>

      <HelpHint
        v-if="step === 1"
        icon="🎓"
        tone="tip"
        title="新手提示"
        text="训练前请准备约 8-10 分钟的授权干声素材，要求背景安静、无回声、单声道。按照 ① 创建音色 → ② 上传素材 → ③ 训练 → ④ 试听 的顺序操作即可。"
        closable
      />

      <StepTabs :steps="steps" :current="step" :done-until="step - 1" @select="onStepSelect" />

      <div class="studio-pipeline" aria-label="训练流水线">
      <div v-for="(node, i) in pipeline" :key="node.key" class="studio-pipeline__item">
        <span
          v-if="i > 0"
          class="studio-pipeline__line"
          :class="{ 'studio-pipeline__line--done': pipeline[i - 1]?.done }"
          aria-hidden="true"
        />
        <div
          class="studio-pipeline__node"
          :class="{
            'studio-pipeline__node--done': node.done,
            'studio-pipeline__node--active': node.active,
          }"
        >
          <span class="studio-pipeline__dot" aria-hidden="true">
            {{ node.done ? "✓" : i + 1 }}
          </span>
          <span class="studio-pipeline__label">{{ node.label }}</span>
        </div>
      </div>
      </div>

      <div class="studio-grid studio-grid--fill">
      <div class="studio-main">
        <ErrorBanner
          v-if="error"
          :message="error"
          @dismiss="error = ''"
        />

        <RackPanel v-show="step === 1" label="步骤 ①" title="创建音色">
          <div class="field" style="margin-bottom: 0.65rem">
            <label for="voiceName">音色名称</label>
            <input id="voiceName" v-model="voiceName" placeholder="旁白男声-001" />
          </div>
          <div class="alert alert--compliance" style="margin-bottom: 0.65rem">
            请仅上传<strong>本人或已获授权</strong>的声纹素材。
          </div>
          <button type="button" class="btn btn--primary" :disabled="busy || kycBlocked" @click="runStep1">
            创建并提交授权
          </button>
          <p v-if="kycBlocked" class="hint" style="margin-top: 10px">
            完成 <router-link to="/kyc">实名认证</router-link> 后可继续训练。
          </p>
        </RackPanel>

        <RackPanel v-show="step === 2" label="步骤 ②" title="上传素材">
          <template #actions>
            <span v-if="voiceId" class="rack-label">{{ voiceId.slice(0, 10) }}…</span>
          </template>
          <div class="field">
            <label for="refText">参考文本</label>
            <textarea id="refText" v-model="refText" placeholder="与 wav 朗读内容一致…" />
            <p class="field-hint">用于质检与训练对齐</p>
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
              <p v-if="audioFile" class="upload-zone__name">{{ audioFile.name }}</p>
              <p v-else class="hint">点击选择 WAV 文件</p>
              <p class="field-hint">单声道 · 无 BGM · 8–10 分钟</p>
              <input ref="fileInputRef" type="file" accept=".wav,audio/wav" @change="onFileChange" />
            </div>
            <p v-if="busy" class="hint" style="margin-top: 8px">上传处理中…</p>
          </div>

          <div class="alert alert--warn" style="margin-bottom: 0.65rem">
            短样本测试：<code>QC_DEV_RELAX_DURATION=true</code>
          </div>

          <div class="row">
            <button type="button" class="text-action" :disabled="busy" @click="goBack">上一步</button>
            <button type="button" class="btn btn--primary" :disabled="busy" @click="runStep2">上传并锁定</button>
          </div>
        </RackPanel>

        <RackPanel v-show="step === 3" label="步骤 ③" title="训练音色" brushed>
          <template #actions>
            <span v-if="assetId" class="rack-label">{{ assetId.slice(0, 10) }}…</span>
          </template>
          <div v-if="devMode" class="alert alert--info" style="margin-bottom: 0.65rem">
            默认 <code>TRAIN_MOCK=true</code> 占位训练；真微调需 GPU 或 <code>ENGINE_TRAIN_*</code>。
          </div>
          <div class="row">
            <button type="button" class="text-action" :disabled="busy" @click="goBack">上一步</button>
            <button type="button" class="btn btn--primary" :disabled="busy" @click="runStep3">开始训练</button>
          </div>
        </RackPanel>

        <div v-show="step === 4" class="studio-make-wrap">
          <MakeWorkspace
            v-model:segments="segments"
            v-model:multi-mode="multiMode"
            v-model:voice-id="voiceVersionId"
            v-model:ai-ack="aiAck"
            v-model:speed="speed"
            v-model:temperature="temperature"
            variant="studio"
            :voices="studioVoices"
            :voice-title="voiceName"
            :voice-subtitle="voiceVersionId ? voiceVersionId.slice(0, 16) + '…' : ''"
            :busy="busy"
            :audio-url="audioUrl"
            generate-label="开始合成"
            @generate="runStep4"
          />
        </div>
      </div>

      <aside class="studio-sidebar">
        <RackPanel label="日志" title="操作记录" body-class="studio-log-body">
          <div class="log-panel studio-log-panel">{{ logText }}</div>
        </RackPanel>
      </aside>
      </div>
    </PageSurface>
  </div>
</template>

<style scoped>
.studio-make-wrap {
  min-height: 0;
}
</style>
