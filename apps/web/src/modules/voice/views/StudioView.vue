<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { fetchKycStatus } from "@/api/kyc";
import {
  confirmAsset,
  createConsent,
  createVoice,
  exportDownloadUrl,
  fetchQuota,
  fetchPlatformCapabilities,
  pollJob,
  startTrain,
  importEngineWeightsUpload,
  synthesize,
  uploadAsset,
  getJob,
  type QuotaSummary,
} from "@/api/client";
import { fetchVoiceVersions } from "@/api/library";
import MakeWorkspace from "@/modules/produce/components/MakeWorkspace.vue";
import CloudGpuConnectForm from "@/modules/voice/components/studio/CloudGpuConnectForm.vue";
import { previewCloudDataset, type DatasetPreviewResult } from "@/api/cloudTrain";
import ErrorBanner from "@/components/ErrorBanner.vue";
import HelpHint from "@/components/HelpHint.vue";
import PageHero from "@/components/PageHero.vue";
import PageSurface from "@/components/PageSurface.vue";
import StepTabs from "@/components/StepTabs.vue";
import RackPanel from "@/modules/voice/components/studio/RackPanel.vue";
import QuotaUsageMeters from "@/components/QuotaUsageMeters.vue";
import TapeReel from "@/modules/voice/components/studio/TapeReel.vue";
import { useWorkspaceShell } from "@/composables/useWorkspaceShell";
import { PAGE_META } from "@/config/navigation";
import { clearAppSession } from "@/utils/session";
import {
  formatAssetDurationZh,
  formatDurationSec,
  jobStatusZh,
  sanitizeWorkerError,
  shortId,
  trainPhaseLabel,
} from "@/utils/studioLogFormat";
import { buildSynthesisPayload, estimateSynthPollTimeoutMs, newSegment, validateSynthesisScript } from "@/modules/produce/types/script";
import {
  appendStudioLog,
  clearStudioWorkspace,
  discardStaleTrainJob,
  followStudioJob,
  isPolling as studioJobPolling,
  loadStudioWorkspace,
  loadStudioActiveJob,
  resumeStudioJobIfNeeded,
  saveStudioWorkspace,
  type StudioActiveJobMeta,
  type StudioWorkspaceSnapshot,
} from "@/modules/voice/composables/useStudioSession";
import type { JobResponse } from "@/types/api";

const router = useRouter();
const { devMode } = useWorkspaceShell();
const studioMeta = PAGE_META.studio;
const quota = ref<QuotaSummary | null>(null);
const trainQuotaBlocked = computed(
  () => quota.value != null && quota.value.trainings_remaining < 1,
);

const DRY_VOCAL_REF_TEXT =
  "好好爱自己，就有人会爱你，这乐观的说词，幸福的样子，我感觉好真实。";
const DRY_VOCAL_SAMPLE_WAV = "/samples/keyword_vocal_9s.wav";
const DEFAULT_SYNTH_PREVIEW_TEXT = "你好，这是一次语音合成测试。";
const QUICK_CLONE_SPEED = 1.0;
const QUICK_CLONE_TEMPERATURE = 0.68;

const voiceName = ref("我的音色");
const voiceId = ref("");
const assetId = ref("");
const voiceVersionId = ref("");
const refText = ref("");
const refTextAuto = ref(false);
const segments = ref([newSegment("", DEFAULT_SYNTH_PREVIEW_TEXT)]);
const multiMode = ref(false);
const speed = ref(QUICK_CLONE_SPEED);
const temperature = ref(QUICK_CLONE_TEMPERATURE);
const aiAck = ref(true);
const audioFile = ref<File | null>(null);
const audioUrl = ref("");
const lastSynthJobId = ref("");
const fileInputRef = ref<HTMLInputElement | null>(null);

const step = ref(1);
const busy = ref(false);
const busyLabel = ref("处理中…");
const error = ref("");
const logLines = ref<string[]>([]);
const kycVerified = ref<boolean | null>(null);
const trainModeLabel = ref("");
const engineMock = ref(true);
const asrAvailable = ref(false);
const cloudTrainAvailable = ref(false);
const weightImportAvailable = ref(false);
const quickCloneAvailable = ref(true);
const STEP3_MODE_KEY = "studio_step3_mode";

const cloudGpuConnected = ref(false);
const cloudLocalDatasetPrep = ref(true);
const cloudUseAsr = ref(true);
const cloudTrainGptEpochs = ref(8);
const cloudTrainSovitsEpochs = ref(8);
const cloudTrainEpochLabel = ref("8+8");
const assetDurationSec = ref(0);
const datasetPreview = ref<DatasetPreviewResult | null>(null);
const step3Mode = ref<"quick" | "cloud" | "import">("quick");
const gptWeightFile = ref<File | null>(null);
const sovitsWeightFile = ref<File | null>(null);
const gptInputRef = ref<HTMLInputElement | null>(null);
const sovitsInputRef = ref<HTMLInputElement | null>(null);
const tunePending = ref(false);
const kycBlocked = computed(() => kycVerified.value === false);
const longAsset = computed(() => assetDurationSec.value > 60);
const cloudIdealAsset = computed(() => assetDurationSec.value >= 30 * 60);
const quickCloneMisuse = computed(() => step3Mode.value === "quick" && longAsset.value);
const studioLocked = computed(() => busy.value || studioJobPolling.value);
const showBusyOverlay = computed(() => busy.value);
const trainProgressLine = ref("");
const trainProgressPhase = ref("");
const trainRemotePath = ref("");
const trainRemoteSegments = ref<number | null>(null);
const synthExportHref = computed(() =>
  lastSynthJobId.value ? exportDownloadUrl(lastSynthJobId.value) : "",
);
const busyOverlayLabel = computed(() =>
  busy.value ? busyLabel.value : studioJobPolling.value ? "训练任务进行中…" : "",
);

const steps = [
  { n: 1, label: "创建音色", desc: "命名并提交声纹授权" },
  { n: 2, label: "上传素材", desc: "干声最长 1 小时" },
  { n: 3, label: "克隆", desc: "快速克隆 / 云端 / 导入权重" },
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

const assetDurationLabel = computed(() =>
  assetDurationSec.value > 0 ? formatAssetDurationZh(assetDurationSec.value) : null,
);

const step3ModeLabel = computed(() => {
  if (step3Mode.value === "cloud") return "云端完整微调";
  if (step3Mode.value === "import") return "导入外部权重";
  return "快速克隆";
});

const cloudPrepSummary = computed(() => {
  if (!cloudLocalDatasetPrep.value) return "整段上传 · 远端 FunASR 切分";
  if (cloudUseAsr.value && asrAvailable.value) return "本机切分 · 逐段 ASR 对齐";
  return "本机切分 · 参考文本均分";
});

const refTextExcerpt = computed(() => {
  const t = refText.value.trim();
  if (!t) return null;
  return t.length > 72 ? `${t.slice(0, 72)}…` : t;
});

const cloudTrainPhaseSteps = [
  { key: "upload", label: "上传" },
  { key: "preprocess", label: "预处理" },
  { key: "gpt", label: "GPT" },
  { key: "sovits", label: "SoVITS" },
  { key: "done", label: "完成" },
] as const;

const cloudTrainPhaseIndex = computed(() => {
  const phase = trainProgressPhase.value;
  if (!phase) return studioJobPolling.value ? 0 : -1;
  if (phase === "upload_done") return 0;
  if (phase.startsWith("preprocess")) return 1;
  if (phase.startsWith("gpt")) return 2;
  if (phase.startsWith("sovits")) return 3;
  if (phase === "done") return 4;
  if (phase === "starting") return 0;
  return -1;
});

const cloudEstMinutes = computed(() => {
  const segs = datasetPreview.value?.segment_count ?? (assetDurationSec.value > 60 ? 35 : 12);
  const low = Math.max(8, Math.round((segs / 37) * 10));
  const high = Math.max(low + 8, Math.round((segs / 37) * 25));
  return { low, high };
});

const pipeline = computed(() => [
  { key: "voice", label: "音色", done: !!voiceId.value, active: step.value === 1 },
  { key: "asset", label: "素材", done: !!assetId.value, active: step.value === 2 },
  { key: "train", label: "训练", done: !!voiceVersionId.value, active: step.value === 3 },
  { key: "synth", label: "试听", done: !!audioUrl.value, active: step.value === 4 },
]);

function pushLog(line: string) {
  logLines.value.push(`[${new Date().toLocaleTimeString()}] ${line}`);
  persistWorkspace();
}

function snapshotWorkspace(): StudioWorkspaceSnapshot {
  return {
    voiceId: voiceId.value,
    voiceName: voiceName.value,
    assetId: assetId.value,
    voiceVersionId: voiceVersionId.value,
    refText: refText.value,
    refTextAuto: refTextAuto.value,
    step: step.value,
    step3Mode: step3Mode.value,
    assetDurationSec: assetDurationSec.value,
    logLines: [...logLines.value],
    audioUrl: audioUrl.value,
    lastSynthJobId: lastSynthJobId.value,
    segmentText: segments.value[0]?.text ?? "",
  };
}

function applyWorkspace(ws: StudioWorkspaceSnapshot) {
  voiceId.value = ws.voiceId;
  voiceName.value = ws.voiceName;
  assetId.value = ws.assetId;
  voiceVersionId.value = ws.voiceVersionId;
  refText.value = ws.refText;
  refTextAuto.value = ws.refTextAuto;
  step.value = ws.step;
  step3Mode.value = ws.step3Mode;
  assetDurationSec.value = ws.assetDurationSec;
  logLines.value = [...ws.logLines];
  audioUrl.value = ws.audioUrl ?? "";
  lastSynthJobId.value = ws.lastSynthJobId ?? "";
  const restoredText = ws.segmentText?.trim();
  if (restoredText && segments.value[0]) {
    segments.value = [{ ...segments.value[0], text: restoredText }];
  }
  if (voiceVersionId.value) {
    segments.value = segments.value.map((s) => ({ ...s, voiceVersionId: voiceVersionId.value }));
  }
}

function persistWorkspace() {
  if (!voiceId.value && !assetId.value && !logLines.value.length) return;
  saveStudioWorkspace(snapshotWorkspace());
}

function formatRemoteDatasetLog(job: JobResponse): string | null {
  const path = job.train_remote_dataset_path ?? job.train_remote_work_dir;
  if (!path) return null;
  const segs =
    job.train_dataset_segments != null ? `${job.train_dataset_segments}段 · ` : "";
  return `远端数据 · ${segs}${path}`;
}

function applyQuickCloneStableTune() {
  speed.value = QUICK_CLONE_SPEED;
  temperature.value = QUICK_CLONE_TEMPERATURE;
}

function syncQuickCloneSynthPreview() {
  if (step3Mode.value !== "quick") return;
  const ref = refText.value.trim();
  if (!ref || !segments.value[0]) return;
  const current = segments.value[0].text.trim();
  if (!current || current === DEFAULT_SYNTH_PREVIEW_TEXT) {
    segments.value = [{ ...segments.value[0], text: ref }];
  }
}

async function applyTrainJobResult(job: JobResponse, isCloud: boolean) {
  if (job.status === "succeeded" && job.voice_version_id) {
    voiceVersionId.value = job.voice_version_id;
    segments.value = segments.value.map((s) => ({ ...s, voiceVersionId: voiceVersionId.value }));
    audioUrl.value = "";
    lastSynthJobId.value = "";
    if (isCloud && job.train_gpt_epochs != null && job.train_sovits_epochs != null) {
      const elapsed =
        job.train_elapsed_sec != null ? formatDurationSec(job.train_elapsed_sec) : "—";
      const segs =
        job.train_dataset_segments != null ? `${job.train_dataset_segments}段` : "—";
      pushLog(
        `训练完成 · GPT ${job.train_gpt_epochs}+${job.train_sovits_epochs} · ${segs} · 远端 ${elapsed} · #${shortId(voiceVersionId.value)}`,
      );
      const remoteLog = formatRemoteDatasetLog(job);
      if (remoteLog) pushLog(`  ${remoteLog}`);
      if (job.train_remote_dataset_path) trainRemotePath.value = job.train_remote_dataset_path;
      if (job.train_dataset_segments != null) trainRemoteSegments.value = job.train_dataset_segments;
      if (
        job.train_elapsed_sec != null &&
        job.train_elapsed_sec < 600 &&
        (job.train_gpt_epochs ?? 0) >= 8
      ) {
        pushLog(
          `提示 · 远端仅 ${formatDurationSec(job.train_elapsed_sec)}，强 GPU 上可能正常；合成仍差请检查参考片段与 ASR 对齐`,
        );
      }
    } else {
      pushLog(`训练完成 · #${shortId(voiceVersionId.value)}`);
    }
    step.value = 4;
    trainProgressLine.value = "";
    trainProgressPhase.value = "";
    persistWorkspace();
    if (isCloud) {
      pushLog("训练完成，正在自动生成试听（首次加载权重可能需 2–4 分钟）…");
      await runStep4();
    } else if (step3Mode.value === "quick") {
      syncQuickCloneSynthPreview();
      pushLog("快速克隆完成，正在自动生成试听…");
      await runStep4();
    }
    return;
  }
  throw new Error(
    sanitizeWorkerError(
      job.error_message ??
        (isCloud
          ? "云端训练失败，详见 train.log"
          : "快速克隆失败，请确认 TRAIN_MOCK=false 且引擎 9880 已启动"),
    ),
  );
}

function logJobStatus(prefix: string, status: string, last: { value: string }) {
  if (status === last.value) return;
  last.value = status;
  if (status === "failed") return;
  if (status === "succeeded") {
    pushLog(`${prefix}完成`);
    return;
  }
  pushLog(`${prefix}${jobStatusZh(status)}`);
}

function logTrainJobTick(job: JobResponse, last: { status: string; phase: string; upload: boolean }) {
  const phase = job.train_progress_phase ?? "";
  const msg = job.train_progress_message ?? "";
  if (msg) trainProgressLine.value = msg;
  else if (job.status === "running") trainProgressLine.value = "云端 GPU 微调中…";
  else if (job.status === "queued") trainProgressLine.value = "排队等待 Worker…";

  if (!last.upload && (phase === "upload_done" || job.train_remote_dataset_path)) {
    last.upload = true;
    if (job.train_remote_dataset_path) trainRemotePath.value = job.train_remote_dataset_path;
    if (job.train_dataset_segments != null) trainRemoteSegments.value = job.train_dataset_segments;
    const remoteLog = formatRemoteDatasetLog(job);
    if (remoteLog) pushLog(`  ${remoteLog}`);
  }

  if (phase) trainProgressPhase.value = phase;

  if (job.status !== last.status) {
    last.status = job.status;
    if (job.status === "failed") {
      pushLog(`训练失败 · ${sanitizeWorkerError(job.error_message)}`);
    } else if (job.status !== "succeeded") {
      pushLog(`训练${jobStatusZh(job.status)}`);
    }
  }
  if (phase && phase !== last.phase) {
    last.phase = phase;
    const label = msg && msg.length <= 48 ? msg : trainPhaseLabel(phase);
    if (phase.endsWith("_done") || phase === "done") {
      pushLog(`  ✓ ${label}`);
    } else if (phase.endsWith("_running")) {
      trainProgressLine.value = label;
    }
  }
}

async function tryRestoreSynthResult() {
  if (audioUrl.value) return;
  const jobId = lastSynthJobId.value;
  if (!jobId) return;
  try {
    const job = await getJob(jobId);
    if (job.status === "succeeded" && job.audio_url) {
      audioUrl.value = job.audio_url;
      pushLog(`已恢复上次合成试听`);
    }
  } catch {
    /* ignore */
  }
}

async function tryResumeTrainJob() {
  const ws = loadStudioWorkspace();
  if (ws?.voiceId) applyWorkspace(ws);
  await discardStaleTrainJob(ws);
  if (!loadStudioActiveJob() && !studioJobPolling.value) return;
  // 已在步骤 ④ 且音色版本就绪：不再阻塞合成区，仅后台跟训练任务
  const blocking = !(voiceVersionId.value && step.value >= 4);
  const statusLast = { value: "" };
  const phaseLast = { status: "", phase: "", upload: false };
  const onTick = (j: JobResponse) => {
    logJobStatus("训练", j.status, statusLast);
    if (step3Mode.value === "cloud") logTrainJobTick(j, phaseLast);
  };
  try {
    const job = await resumeStudioJobIfNeeded(onTick);
    if (!job || job.job_type !== "train") return;
    if (job.status === "succeeded") {
      await applyTrainJobResult(job, step3Mode.value === "cloud");
      quota.value = await fetchQuota().catch(() => quota.value);
    } else if (job.status === "failed") {
      pushLog(`训练失败 · ${sanitizeWorkerError(job.error_message)}`);
      if (step3Mode.value === "quick") {
        void recoverVoiceVersionAfterTrainFailure();
      }
    }
  } catch (e) {
    if (blocking) error.value = formatApiError(e);
  } finally {
    /* 云端训练在后台轮询，不占用全屏遮罩 */
  }
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
  try {
    const caps = await fetchPlatformCapabilities();
    trainModeLabel.value = caps.train_mode_label;
    engineMock.value = caps.engine_mock;
    asrAvailable.value = caps.asr_enabled && caps.asr_available;
    cloudTrainAvailable.value = caps.cloud_train_self_service ?? caps.cloud_train_available;
    weightImportAvailable.value = caps.weight_import_available;
    quickCloneAvailable.value = caps.quick_clone_available;
    cloudGpuConnected.value = caps.cloud_train_user_connected ?? false;
    cloudLocalDatasetPrep.value = caps.cloud_train_local_dataset_prep_default ?? true;
    cloudUseAsr.value = caps.cloud_train_use_asr_default ?? asrAvailable.value;
    cloudTrainGptEpochs.value = caps.cloud_train_gpt_epochs ?? 8;
    cloudTrainSovitsEpochs.value = caps.cloud_train_sovits_epochs ?? 8;
    cloudTrainEpochLabel.value = caps.cloud_train_epoch_label ?? "8+8";
    const savedMode = sessionStorage.getItem(STEP3_MODE_KEY);
    if (savedMode === "cloud" && cloudTrainAvailable.value) {
      step3Mode.value = "cloud";
    } else if (savedMode === "import" && weightImportAvailable.value) {
      step3Mode.value = "import";
    } else {
      step3Mode.value = "quick";
    }
  } catch {
    trainModeLabel.value = "";
  }
  void tryResumeTrainJob();
  void tryRestoreSynthResult();
});

watch(
  [voiceId, assetId, voiceVersionId, step, refText],
  () => persistWorkspace(),
);

watch(step3Mode, (mode) => {
  sessionStorage.setItem(STEP3_MODE_KEY, mode);
  if (mode !== "cloud") datasetPreview.value = null;
  if (mode === "quick") applyQuickCloneStableTune();
});

watch(step, (s) => {
  if (s === 4 && step3Mode.value === "quick") syncQuickCloneSynthPreview();
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

async function loadDryVocalSample() {
  error.value = "";
  busy.value = true;
  busyLabel.value = "加载样本…";
  try {
    clearStudioWorkspace();
    voiceId.value = "";
    resetTrainingArtifacts();
    lastSynthJobId.value = "";
    refTextAuto.value = false;
    step.value = 1;
    voiceName.value = "关键词-干声9秒";
    refText.value = DRY_VOCAL_REF_TEXT;
    logLines.value = [];
    const resp = await fetch(DRY_VOCAL_SAMPLE_WAV);
    if (!resp.ok) {
      throw new Error("样本未找到，请运行 scripts/prep_studio_dry_vocal_clip.py --copy-public");
    }
    const blob = await resp.blob();
    audioFile.value = new File([blob], "keyword_vocal_9s.wav", { type: "audio/wav" });
    pushLog("摸底：已重置 Studio 会话并加载 9 秒干声（请从步骤 ① 创建音色）");
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    busy.value = false;
  }
}

function resetTrainingArtifacts() {
  voiceVersionId.value = "";
  assetId.value = "";
  audioUrl.value = "";
  audioFile.value = null;
  assetDurationSec.value = 0;
  datasetPreview.value = null;
  segments.value = segments.value.map((s) => ({ ...s, voiceVersionId: "" }));
}

async function runStep1() {
  if (kycBlocked.value) {
    error.value = "请先完成实名认证后再创建音色。";
    return;
  }
  error.value = "";
  busy.value = true;
  busyLabel.value = "创建音色…";
  resetTrainingArtifacts();
  try {
    const v = await createVoice(voiceName.value.trim());
    voiceId.value = v.voice_id;
    pushLog(`音色 #${shortId(v.voice_id)}`);
    const c = await createConsent(voiceId.value);
    pushLog(`授权 ${jobStatusZh(c.status)}`);
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
    error.value = "还没有选择音频——点击上传区选择音频文件（wav / m4a / mp3 / flac）";
    return;
  }
  if (!refText.value.trim() && !asrAvailable.value) {
    error.value = "请填写参考文本，或重启平台以自动安装 ASR（platform_start）";
    return;
  }
  error.value = "";
  busy.value = true;
  busyLabel.value = asrAvailable.value && !refText.value.trim() ? "上传并识别参考文本…" : "上传并质检…";
  voiceVersionId.value = "";
  audioUrl.value = "";
  refTextAuto.value = false;
  try {
    const up = await uploadAsset(voiceId.value, audioFile.value, refText.value.trim());
    assetId.value = up.asset_id;
    pushLog(`素材 #${shortId(up.asset_id)} · 上传${up.qc_passed ? " · QC 通过" : " · QC 未过"}`);
    if (up.qc_result?.audio_enhanced) {
      pushLog("素材已自动增强：高通/压缩/响度归一，利于云端训练吐字");
    }
    if (!up.qc_passed) {
      const issues = up.qc_result?.issues?.map((i) => i.message).join("; ") ?? "质检未通过";
      throw new Error(issues);
    }
    const recognized = up.qc_result?.ref_text?.trim() ?? "";
    if (!recognized) {
      const hint = up.qc_result?.issues?.map((i) => i.message).join("; ");
      throw new Error(hint || "未能获得参考文本，请手动填写后重新上传");
    }
    refText.value = recognized;
    refTextAuto.value = Boolean(up.qc_result?.ref_text_auto);
    assetDurationSec.value = up.qc_result?.duration_sec ?? 0;
    datasetPreview.value = null;
    if (assetDurationSec.value > 0) {
      pushLog(`时长 ${formatAssetDurationZh(assetDurationSec.value)}`);
    }
    if (refTextAuto.value) {
      pushLog(`参考文本 · ASR（${up.qc_result?.asr_provider ?? "auto"}）`);
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

function onGptWeightChange(e: Event) {
  const input = e.target as HTMLInputElement;
  gptWeightFile.value = input.files?.[0] ?? null;
}

function onSovitsWeightChange(e: Event) {
  const input = e.target as HTMLInputElement;
  sovitsWeightFile.value = input.files?.[0] ?? null;
}

async function runDatasetPreview() {
  if (!assetId.value) {
    error.value = "请先完成步骤 ② 上传并锁定素材";
    return;
  }
  error.value = "";
  busy.value = true;
  busyLabel.value = cloudUseAsr.value && asrAvailable.value ? "切分、ASR 与 AI 标注…" : "切分并对齐…";
  try {
    datasetPreview.value = await previewCloudDataset(
      assetId.value,
      cloudLocalDatasetPrep.value ? cloudUseAsr.value : undefined,
      true,
    );
    const enrich = datasetPreview.value.enrich_mode;
    const enrichNote =
      enrich === "llm" ? " · AI校正+情感" : enrich === "keyword" ? " · 规则情感" : "";
    pushLog(
      `切分预览 · ${datasetPreview.value.segment_count}段 · ${datasetPreview.value.mode}${enrichNote} · ${Math.round(datasetPreview.value.source_duration_sec)}s`,
    );
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      error.value = "切分预览超时（长音频逐段 ASR 较慢）。可先关闭「逐段 ASR」再预览，或耐心等待。";
    } else {
      error.value = formatApiError(e);
    }
  } finally {
    busy.value = false;
  }
}

async function recoverVoiceVersionAfterTrainFailure(): Promise<boolean> {
  if (!voiceId.value) return false;
  try {
    const versions = await fetchVoiceVersions();
    const latest = versions
      .filter((v) => v.voice_id === voiceId.value && v.synth_ready !== false)
      .sort((a, b) => (b.version ?? 0) - (a.version ?? 0))[0];
    if (!latest?.voice_version_id) return false;
    voiceVersionId.value = latest.voice_version_id;
    segments.value = segments.value.map((s) => ({ ...s, voiceVersionId: latest.voice_version_id }));
    step.value = 4;
    persistWorkspace();
    pushLog(`已恢复最新音色版本 · #${shortId(latest.voice_version_id)} · v${latest.version}`);
    return true;
  } catch {
    return false;
  }
}

async function runStep3() {
  if (step3Mode.value === "import") {
    await runStep3Import();
    return;
  }
  if (!voiceId.value || !assetId.value) {
    error.value = "请先完成上传——返回步骤 ② 选择并锁定素材";
    return;
  }
  if (step3Mode.value === "cloud" && !cloudGpuConnected.value) {
    error.value = "请先填写并保存云端 GPU 连接信息（保存并验证）";
    return;
  }
  if (step3Mode.value === "cloud" && cloudLocalDatasetPrep.value && !datasetPreview.value) {
    const ok = window.confirm(
      "尚未预览本机切分效果。建议先点「预览切分」试听各段文本是否对齐，再继续云端训练。是否仍要开始？",
    );
    if (!ok) return;
  }
  if (step3Mode.value === "quick" && !quickCloneAvailable.value) {
    error.value = "快速克隆不可用——请确认 TRAIN_MOCK=false 后重启平台";
    return;
  }
  if (kycVerified.value === false) {
    error.value = "请先完成实名认证后再训练";
    router.push("/kyc");
    return;
  }
  if (quota.value && quota.value.trainings_remaining < 1) {
    error.value = `本月训练次数已用完（${quota.value.trainings_used}/${quota.value.monthly_train_limit}），下月 1 日重置或联系运营提升额度`;
    return;
  }
  busy.value = true;
  const isCloud = step3Mode.value === "cloud";
  const segCount = datasetPreview.value?.segment_count;
  const estLow = segCount ? Math.max(8, Math.round((segCount / 37) * 10)) : 12;
  const estHigh = segCount ? Math.max(estLow + 8, Math.round((segCount / 37) * 25)) : 35;
  busyLabel.value = isCloud
    ? `云端 GPU 微调 ${cloudTrainEpochLabel.value} epoch（约 ${estLow}–${estHigh} 分钟）…`
    : "快速克隆中…";
  try {
    const t = await startTrain(voiceId.value, assetId.value, {
      trainBackend: isCloud ? "cloud" : "quick",
      ...(isCloud
        ? {
            cloudLocalDatasetPrep: cloudLocalDatasetPrep.value,
            cloudUseAsr: cloudLocalDatasetPrep.value ? cloudUseAsr.value : false,
          }
        : {}),
    });
    if (isCloud) {
      const mode = cloudLocalDatasetPrep.value
        ? cloudUseAsr.value
          ? "本机切分+ASR"
          : "本机切分"
        : "远端切分";
      pushLog(
        `云端训练 · GPT ${cloudTrainGptEpochs.value}+${cloudTrainSovitsEpochs.value}` +
          (segCount ? ` · ${segCount}段` : "") +
          ` · ${mode} · 约 ${estLow}–${estHigh} 分钟 · #${shortId(t.job_id)}`,
      );
    } else {
      pushLog(`快速克隆 · #${shortId(t.job_id)}`);
    }
    const pollMs = isCloud ? 7_200_000 : 600_000;
    const meta: StudioActiveJobMeta = {
      jobId: t.job_id,
      kind: "train",
      label: busyLabel.value,
      timeoutMs: pollMs,
      startedAt: new Date().toISOString(),
    };
    if (isCloud) {
      trainProgressLine.value = "排队等待 Worker…";
      trainProgressPhase.value = "";
      trainRemotePath.value = "";
      trainRemoteSegments.value = segCount ?? null;
      busy.value = false;
    }
    let ws = snapshotWorkspace();
    const trainTickLast = { status: "", phase: "", upload: false };
    const job = await followStudioJob(
      meta,
      ws,
      (j) => {
        if (isCloud) logTrainJobTick(j, trainTickLast);
        else logJobStatus("训练", j.status, { value: trainTickLast.status });
      },
    );
    await applyTrainJobResult(job, isCloud);
    quota.value = await fetchQuota().catch(() => quota.value);
  } catch (e) {
    const msg = formatApiError(e);
    if (!isCloud && (await recoverVoiceVersionAfterTrainFailure())) {
      error.value = `${msg} 音色版本已在后台生成，已为你进入步骤 ④，请点「开始合成」试听。`;
    } else {
      error.value = msg;
    }
    if (isCloud && !logLines.value.some((l) => l.includes("训练失败"))) {
      pushLog(`训练失败 · ${sanitizeWorkerError(msg)}`);
    }
  } finally {
    busy.value = false;
  }
}

async function runStep3Import() {
  if (!voiceId.value) {
    error.value = "请先完成步骤 ① 创建音色";
    return;
  }
  if (!gptWeightFile.value || !sovitsWeightFile.value) {
    error.value = "请选择 GPT（.ckpt）和 SoVITS（.pth）权重文件";
    return;
  }
  if (!audioFile.value && !refText.value.trim()) {
    error.value = "导入需要参考音频与参考文本——请返回步骤 ② 上传干声";
    return;
  }
  if (!refText.value.trim()) {
    error.value = "请填写与参考音频对齐的参考文本";
    return;
  }
  const refAudio = audioFile.value;
  if (!refAudio) {
    error.value = "请返回步骤 ② 上传参考干声";
    return;
  }
  if (quota.value && quota.value.trainings_remaining < 1) {
    error.value = `本月训练次数已用完（${quota.value.trainings_used}/${quota.value.monthly_train_limit}），下月 1 日重置或联系运营提升额度`;
    return;
  }
  error.value = "";
  busy.value = true;
  busyLabel.value = "导入权重中…";
  try {
    const v = await importEngineWeightsUpload(
      gptWeightFile.value,
      sovitsWeightFile.value,
      refAudio,
      {
        voiceName: voiceName.value,
        refText: refText.value.trim(),
        voiceId: voiceId.value,
        voiceAssetId: assetId.value || undefined,
      },
    );
    voiceVersionId.value = v.voice_version_id;
    pushLog(`权重已导入 · v${v.version} · #${shortId(v.voice_version_id)}`);
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
    if (voiceId.value && (await recoverVoiceVersionAfterTrainFailure())) {
      /* recovered latest version for this voice */
    } else {
      error.value = "请先完成训练——步骤 ③ 成功后再合成试听";
      return;
    }
  }
  segments.value = segments.value.map((s) => ({
    ...s,
    voiceVersionId: s.voiceVersionId || voiceVersionId.value,
  }));
  const tune = {
    speed: speed.value,
    temperature: temperature.value,
    emotion: null,
    emotionStrength: 0.5,
  };
  const check = validateSynthesisScript(segments.value, tune);
  if (!check.ok) {
    error.value = check.message;
    return;
  }
  error.value = "";
  busy.value = true;
  busyLabel.value = "合成中…";
  audioUrl.value = "";
  try {
    const payload = buildSynthesisPayload(segments.value, tune, voiceVersionId.value);
    const s = await synthesize(payload, aiAck.value);
    pushLog(`合成 · #${shortId(s.job_id)}`);
    lastSynthJobId.value = s.job_id;
    const synthStatusLast = { value: "" };
    const pollMs =
      estimateSynthPollTimeoutMs(segments.value, tune) +
      (step3Mode.value === "cloud" ? 240_000 : 0);
    const job = await pollJob(
      s.job_id,
      (j) => logJobStatus("合成", j.status, synthStatusLast),
      pollMs,
    );
    if (job.status !== "succeeded" || !job.audio_url) {
      throw new Error(job.error_message ?? "合成失败——请确认 infer worker 与引擎是否在运行");
    }
    audioUrl.value = job.audio_url;
    tunePending.value = false;
    pushLog(`合成完成 · ${job.duration_sec != null ? `${job.duration_sec}s` : "—"}`);
    persistWorkspace();
    quota.value = await fetchQuota().catch(() => quota.value);
  } catch (e) {
    if (lastSynthJobId.value) {
      try {
        const job = await getJob(lastSynthJobId.value);
        if (job.status === "succeeded" && job.audio_url) {
          audioUrl.value = job.audio_url;
          tunePending.value = false;
          pushLog(`合成完成 · ${job.duration_sec != null ? `${job.duration_sec}s` : "—"}（后台已完成）`);
          persistWorkspace();
          quota.value = await fetchQuota().catch(() => quota.value);
          return;
        }
      } catch {
        /* ignore */
      }
    }
    error.value = formatApiError(e);
  } finally {
    busy.value = false;
  }
}

function logout() {
  clearAppSession();
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
    <div v-if="showBusyOverlay" class="busy-overlay" aria-live="polite">
      <div class="busy-overlay__box rack-panel">
        <span v-for="n in 4" :key="n" class="rack-screw" :class="`rack-screw--${['tl', 'tr', 'bl', 'br'][n - 1]}`" aria-hidden="true" />
        <TapeReel :spinning="true" :size="72" />
        <p class="rack-title" style="margin: 16px 0 4px">{{ busyOverlayLabel }}</p>
        <p class="hint">短操作完成后自动关闭</p>
      </div>
    </div>

    <PageSurface>
      <PageHero compact flow title="训练工作台" :hint="studioMeta.desc">
      <template #stats>
        <p class="page-metrics">
          步骤 <strong class="page-metrics__accent">{{ step }}/4</strong>
          <span v-if="assetDurationLabel && step >= 3" class="page-metrics__muted"> · 素材 {{ assetDurationLabel }}</span>
          <span v-if="trainModeLabel" class="page-metrics__muted"> · {{ trainModeLabel }}</span>
        </p>
      </template>
      <template #actions>
        <div class="hero-actions">
          <router-link v-if="voiceVersionId" :to="`/quality/${voiceVersionId}`" class="text-action">AB 测评</router-link>
          <button type="button" class="text-action text-action--danger" @click="logout">退出</button>
        </div>
      </template>
      </PageHero>

      <QuotaUsageMeters v-if="quota" :quota="quota" layout="panel" class="studio-quota-panel" />

      <div v-if="kycVerified === false" class="alert alert--warn studio-kyc">
        训练自有声纹前需完成<strong>实名认证</strong>。
        <router-link to="/kyc" class="text-action">去认证</router-link>
      </div>
      <div v-else-if="trainQuotaBlocked" class="alert alert--warn studio-kyc">
        本月<strong>训练次数</strong>已用完（{{ quota?.trainings_used }}/{{ quota?.monthly_train_limit }}）。
        下月 1 日自动重置，或联系运营提升额度。仍可「导入外部权重」跳过训练。
      </div>
      <p v-else-if="kycVerified === null" class="hint studio-kyc-hint">正在检查实名状态…</p>

      <HelpHint
        v-if="step === 1"
        icon="🎓"
        tone="tip"
        title="新手提示"
        text="快速克隆用几秒参考即可；云端完整微调建议准备 30–45 分钟干净干声（最长 1 小时），整段会切分后用于 GPU 微调，只有步骤 ④ 试听才取 3–10 秒参考片段（引擎限制）。"
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
          <ul class="studio-checklist">
            <li>单声道干声，背景安静、无 BGM / 回声</li>
            <li>云端完整微调建议 <strong>30–45 分钟</strong>干声（最长 1 小时），整段用于切分训练</li>
            <li>步骤 ④ 合成试听仅取 3–10 秒参考片段，<strong>不影响</strong>训练用素材长度</li>
            <li>快速克隆只需 <strong>3–9 秒</strong>清晰片段 + 对齐参考文本</li>
            <li>支持 wav / m4a / mp3 / flac，m4a 上传后自动转 wav</li>
            <li>上传后平台会<strong>自动增强</strong>：去低频噪声、轻压缩、响度归一，让吐字更清晰洪亮（需本机 ffmpeg）</li>
          </ul>
          <div class="field">
            <label for="refText">参考文本 <span class="hint">（须与参考音频里说的话一致）</span></label>
            <textarea id="refText" v-model="refText" placeholder="填写音频前 3–9 秒实际台词；留空则 ASR 自动识别" />
            <p v-if="refTextAuto" class="field-hint">已由 ASR 识别前 9 秒，请核对后快速克隆（勿填整段长稿）</p>
            <p v-else-if="asrAvailable" class="field-hint">留空则识别前 9 秒；手动填写时只需写这段音频里的台词，不是步骤 ④ 试听句</p>
            <p v-else class="field-hint">ASR 未就绪时需手动填写；重启平台后会自动安装（platform_start）</p>
          </div>

          <div class="field">
            <label>音频文件</label>
            <div class="row" style="margin-bottom: 0.5rem; gap: 0.75rem; flex-wrap: wrap">
              <button type="button" class="text-action" :disabled="busy" @click="loadDryVocalSample">
                使用 9 秒干声样本
              </button>
              <span class="hint">单声道 32kHz · 与参考文本逐字对齐 · 适合快速克隆</span>
            </div>
            <div
              class="upload-zone"
              :class="{ 'has-file': !!audioFile }"
              role="button"
              tabindex="0"
              @click="pickFile"
              @keydown.enter="pickFile"
            >
              <p v-if="audioFile" class="upload-zone__name">{{ audioFile.name }}</p>
              <p v-else class="hint">点击选择音频（wav / m4a / mp3 / flac）</p>
              <p class="field-hint">单声道 · 无 BGM · m4a 上传后自动转 wav</p>
              <input ref="fileInputRef" type="file" accept=".wav,.m4a,.mp3,.flac,audio/wav,audio/mp4,audio/mpeg,audio/flac" @change="onFileChange" />
            </div>
            <p v-if="busy" class="hint" style="margin-top: 8px">上传处理中…</p>
          </div>

          <div v-if="devMode" class="alert alert--warn" style="margin-bottom: 0.65rem">
            开发模式：<code>QC_DEV_RELAX_DURATION=true</code> 可放宽最短时长；上限由 <code>QC_MAX_DURATION_SEC</code> 控制（默认 3600）
          </div>

          <div class="row">
            <button type="button" class="text-action" :disabled="busy" @click="goBack">上一步</button>
            <button type="button" class="btn btn--primary" :disabled="busy" @click="runStep2">上传并锁定</button>
          </div>
        </RackPanel>

        <RackPanel v-show="step === 3" label="步骤 ③" title="选择克隆方式" brushed>
          <template #actions>
            <span v-if="assetId" class="rack-label">{{ assetId.slice(0, 10) }}…</span>
          </template>
          <div v-if="assetId && assetDurationLabel" class="studio-asset-summary">
            <span>已锁定素材 · {{ assetDurationLabel }}</span>
            <span v-if="refTextExcerpt" class="studio-asset-summary__ref" :title="refText">{{ refTextExcerpt }}</span>
          </div>
          <div class="field" style="margin-bottom: 0.75rem">
            <span class="field-label">克隆方式（三选一，互不影响）</span>
            <div class="studio-clone-options">
              <label
                class="studio-clone-option"
                :class="{ 'studio-clone-option--active': step3Mode === 'quick' }"
              >
                <input v-model="step3Mode" type="radio" value="quick" :disabled="!quickCloneAvailable" />
                <span class="studio-clone-option__title">快速克隆</span>
                <span class="studio-clone-option__desc">上传干声即可，秒级完成，无需 GPU / 权重</span>
              </label>
              <label
                v-if="cloudTrainAvailable"
                class="studio-clone-option"
                :class="{ 'studio-clone-option--active': step3Mode === 'cloud' }"
              >
                <input v-model="step3Mode" type="radio" value="cloud" />
                <span class="studio-clone-option__title">云端完整微调</span>
                <span class="studio-clone-option__desc">
                  填写你的 GPU 服务器 SSH，远端训练后拉回权重（需本机 ENGINE_TRAIN_ROOT）
                </span>
              </label>
              <label
                v-if="weightImportAvailable"
                class="studio-clone-option"
                :class="{ 'studio-clone-option--active': step3Mode === 'import' }"
              >
                <input v-model="step3Mode" type="radio" value="import" />
                <span class="studio-clone-option__title">导入外部权重</span>
                <span class="studio-clone-option__desc">AutoDL 等环境已训好的 .ckpt / .pth，上传即用</span>
              </label>
            </div>
            <p v-if="!cloudTrainAvailable && !weightImportAvailable" class="field-hint" style="margin-top: 0.5rem">
              云端微调与权重导入尚未配置时，使用「快速克隆」即可完成试听。
            </p>
          </div>

          <template v-if="step3Mode === 'quick'">
            <div v-if="quickCloneMisuse" class="alert alert--warn" style="margin-bottom: 0.65rem">
              当前素材约 <strong>{{ Math.round(assetDurationSec / 60) }} 分钟</strong>。
              快速克隆<strong>不会</strong>用整段音频训练，只会取前几秒作参考。
              若要完整微调，请改选「<button type="button" class="text-action" @click="step3Mode = 'cloud'">云端完整微调</button>」。
            </div>
            <div v-if="!quickCloneAvailable" class="alert alert--warn" style="margin-bottom: 0.65rem">
              快速克隆需要 <code>TRAIN_MOCK=false</code>。当前为占位训练模式。
            </div>
            <div v-else-if="engineMock" class="alert alert--warn" style="margin-bottom: 0.65rem">
              训练可走快速克隆，但步骤 ④ 合成为 Mock 蜂鸣。请设 <code>ENGINE_MOCK=false</code> 并启动引擎 9880。
            </div>
            <div v-else class="alert alert--info" style="margin-bottom: 0.65rem">
              使用干声前 3–9 秒作参考（zero-shot）。默认<strong>稳态参数</strong>（温度 0.68 / 语速 1.0）减轻电音；素材须干净无 BGM。
            </div>
            <div class="row">
              <button type="button" class="text-action" :disabled="busy" @click="goBack">上一步</button>
              <button type="button" class="btn btn--primary" :disabled="busy || trainQuotaBlocked || !quickCloneAvailable" @click="runStep3">
                开始快速克隆
              </button>
            </div>
          </template>

          <template v-else-if="step3Mode === 'cloud'">
            <div v-if="cloudIdealAsset" class="alert alert--info" style="margin-bottom: 0.65rem">
              当前素材约 <strong>{{ Math.round(assetDurationSec / 60) }} 分钟</strong>，适合云端完整微调。
              训练会使用<strong>整段音频</strong>切分后的全部片段；试听合成时引擎只读取其中 3–10 秒作参考。
            </div>
            <div v-if="studioJobPolling" class="alert alert--info studio-train-active" style="margin-bottom: 0.65rem">
              <strong>{{ busyLabel }}</strong>
              <span v-if="trainProgressLine"> · {{ trainProgressLine }}</span>
              <div v-if="cloudTrainPhaseIndex >= 0" class="studio-phase-bar" aria-label="训练阶段">
                <div
                  v-for="(p, i) in cloudTrainPhaseSteps"
                  :key="p.key"
                  class="studio-phase-bar__step"
                  :class="{
                    'studio-phase-bar__step--done': i < cloudTrainPhaseIndex,
                    'studio-phase-bar__step--active': i === cloudTrainPhaseIndex,
                  }"
                >
                  <span class="studio-phase-bar__dot">{{ i < cloudTrainPhaseIndex ? "✓" : i + 1 }}</span>
                  <span class="studio-phase-bar__label">{{ p.label }}</span>
                </div>
              </div>
              <p v-if="trainRemotePath" class="field-hint studio-remote-path" style="margin: 0.35rem 0 0">
                远端数据：{{ trainRemoteSegments != null ? `${trainRemoteSegments} 段 · ` : "" }}{{ trainRemotePath }}
              </p>
              <p class="field-hint" style="margin: 0.35rem 0 0">
                训练在后台进行；可切换页面，右侧日志与顶部横幅可返回本页。
              </p>
            </div>
            <CloudGpuConnectForm :disabled="studioLocked" @connected="cloudGpuConnected = $event" />
            <div class="field" style="margin-top: 0.65rem">
              <span class="field-label">上传与对齐方式</span>
              <label class="studio-cloud-option">
                <input v-model="cloudLocalDatasetPrep" type="checkbox" :disabled="studioLocked" />
                <span>
                  <strong>本机预处理 dataset</strong>（推荐）
                  <span class="studio-cloud-option__hint">切分干声后再上传，省上行流量；远端只跑微调</span>
                </span>
              </label>
              <label class="studio-cloud-option" :class="{ 'studio-cloud-option--muted': !cloudLocalDatasetPrep }">
                <input
                  v-model="cloudUseAsr"
                  type="checkbox"
                  :disabled="studioLocked || !cloudLocalDatasetPrep || !asrAvailable"
                />
                <span>
                  <strong>长音频逐段 ASR 对齐</strong>
                  <span v-if="asrAvailable" class="studio-cloud-option__hint">
                    长干声（如 30–45 分钟）按段识别文本；关闭则用参考文本均分
                  </span>
                  <span v-else class="studio-cloud-option__hint">
                    本机 ASR 未就绪，将用参考文本均分（重启 platform_start 可安装）
                  </span>
                </span>
              </label>
            </div>
            <div class="studio-config-detail">
              <p class="studio-config-detail__title">本次训练配置</p>
              <dl class="studio-config-detail__grid">
                <div><dt>档位</dt><dd>GPT {{ cloudTrainGptEpochs }} + SoVITS {{ cloudTrainSovitsEpochs }} epoch（{{ cloudTrainEpochLabel }}）</dd></div>
                <div><dt>精度</dt><dd>FP32（<code>is_half=false</code>，避免合成无声）</dd></div>
                <div><dt>数据</dt><dd>{{ cloudPrepSummary }}</dd></div>
                <div><dt>预估</dt><dd>约 {{ cloudEstMinutes.low }}–{{ cloudEstMinutes.high }} 分钟（视 GPU 与段数）</dd></div>
                <div><dt>远端目录</dt><dd><code>…/cloud_train_jobs/&lt;job_id&gt;/dataset</code></dd></div>
                <div><dt>拉回权重</dt><dd>本机 <code>ENGINE_TRAIN_ROOT</code> 下 GPT / SoVITS 权重目录</dd></div>
              </dl>
            </div>
            <div v-if="assetId" class="field" style="margin-bottom: 0.65rem">
              <div class="row" style="gap: 0.5rem; flex-wrap: wrap; align-items: center">
                <button type="button" class="btn btn--ghost" :disabled="studioLocked" @click="runDatasetPreview">
                  预览切分
                </button>
                <span class="field-hint">
                  按上方选项在本机试切分；长音频开 ASR 可能需数分钟
                </span>
                <span v-if="datasetPreview" class="field-hint">
                  {{ datasetPreview.segment_count }} 段 · {{ datasetPreview.mode }}
                  <template v-if="datasetPreview.enrich_mode === 'llm'"> · AI 校正</template>
                  <template v-else-if="datasetPreview.enrich_mode === 'keyword'"> · 规则情感</template>
                  · 源 {{ datasetPreview.source_duration_sec }}s
                </span>
              </div>
              <div v-if="datasetPreview?.segments.length" class="studio-seg-preview">
                <div
                  v-for="seg in datasetPreview.segments"
                  :key="seg.name"
                  class="studio-seg-preview__row"
                >
                  <span class="studio-seg-preview__meta">
                    #{{ seg.index + 1 }} · {{ seg.duration_sec }}s
                    <span v-if="seg.emotion_label" class="studio-seg-preview__emo">{{ seg.emotion_label }}</span>
                  </span>
                  <p v-if="seg.text_original && seg.text_original !== seg.text" class="studio-seg-preview__orig">
                    原 ASR：{{ seg.text_original }}
                  </p>
                  <p class="studio-seg-preview__text">{{ seg.text }}</p>
                  <p v-if="seg.notes" class="studio-seg-preview__note">{{ seg.notes }}</p>
                  <audio :src="seg.audio_url" controls preload="none" class="studio-seg-preview__audio" />
                </div>
              </div>
            </div>
            <div class="row">
              <button type="button" class="text-action" :disabled="studioLocked" @click="goBack">上一步</button>
              <button
                type="button"
                class="btn btn--primary"
                :disabled="studioLocked || !cloudGpuConnected || trainQuotaBlocked"
                @click="runStep3"
              >
                开始云端训练
              </button>
            </div>
          </template>

          <template v-else>
            <div class="alert alert--info" style="margin-bottom: 0.65rem">
              在 AutoDL 等环境完成训练后，将 <code>.ckpt</code> / <code>.pth</code> 下载到本机，在此上传。
              参考音频使用步骤 ② 的干声，参考文本需与音频对齐。
            </div>
            <div class="field">
              <span class="field-label">GPT 权重 (.ckpt)</span>
              <button type="button" class="btn btn--ghost" @click="gptInputRef?.click()">
                {{ gptWeightFile?.name ?? "选择文件" }}
              </button>
              <input ref="gptInputRef" type="file" accept=".ckpt" hidden @change="onGptWeightChange" />
            </div>
            <div class="field" style="margin-top: 0.5rem">
              <span class="field-label">SoVITS 权重 (.pth)</span>
              <button type="button" class="btn btn--ghost" @click="sovitsInputRef?.click()">
                {{ sovitsWeightFile?.name ?? "选择文件" }}
              </button>
              <input ref="sovitsInputRef" type="file" accept=".pth" hidden @change="onSovitsWeightChange" />
            </div>
            <div class="row" style="margin-top: 0.75rem">
              <button type="button" class="text-action" :disabled="busy" @click="goBack">上一步</button>
              <button type="button" class="btn btn--primary" :disabled="busy || trainQuotaBlocked" @click="runStep3">导入并试听</button>
            </div>
          </template>
        </RackPanel>

        <div v-show="step === 4" class="studio-make-wrap">
          <div v-if="voiceVersionId" class="studio-version-banner">
            <span>当前音色版本 <code>#{{ shortId(voiceVersionId) }}</code></span>
            <span v-if="step3ModeLabel" class="studio-version-banner__mode">{{ step3ModeLabel }}</span>
          </div>
          <div v-if="step3Mode === 'quick'" class="alert alert--info studio-synth-hint">
            <strong>参考文本</strong>（步骤 ②）须与参考音频逐字对齐；下方<strong>试听台本</strong>可以是任意新句子。快速克隆会自动用参考文本填充试听（可改）。
          </div>
          <div class="alert alert--info studio-synth-hint">
            合成音频开头含 <strong>短-长-短-短</strong> 合规节奏标识（约 0.75 秒），之后才是正文。若几乎听不到人声，请检查参考文本是否与音频对齐。
          </div>
          <MakeWorkspace
            v-model:segments="segments"
            v-model:multi-mode="multiMode"
            v-model:voice-id="voiceVersionId"
            v-model:ai-ack="aiAck"
            v-model:speed="speed"
            v-model:temperature="temperature"
            v-model:tune-pending="tunePending"
            variant="studio"
            :voices="studioVoices"
            :voice-title="voiceName"
            :voice-subtitle="voiceVersionId ? voiceVersionId.slice(0, 16) + '…' : ''"
            :busy="busy"
            :audio-url="audioUrl"
            :export-href="synthExportHref"
            generate-label="开始合成"
            @generate="runStep4"
          />
        </div>
      </div>

      <aside class="studio-sidebar">
        <RackPanel label="当前" title="工作台状态" body-class="studio-status-body">
          <dl class="studio-status-list">
            <div v-if="voiceName">
              <dt>音色</dt>
              <dd>{{ voiceName }}<span v-if="voiceId" class="studio-status-muted"> · #{{ shortId(voiceId) }}</span></dd>
            </div>
            <div v-if="assetDurationLabel">
              <dt>素材</dt>
              <dd>{{ assetDurationLabel }}<span v-if="assetId" class="studio-status-muted"> · 已锁定</span></dd>
            </div>
            <div v-if="refTextExcerpt">
              <dt>参考文本</dt>
              <dd :title="refText">{{ refTextExcerpt }}</dd>
            </div>
            <div v-if="step >= 3">
              <dt>克隆方式</dt>
              <dd>{{ step3ModeLabel }}</dd>
            </div>
            <div v-if="voiceVersionId">
              <dt>版本</dt>
              <dd><code>#{{ shortId(voiceVersionId) }}</code></dd>
            </div>
            <div v-if="trainRemotePath">
              <dt>远端数据</dt>
              <dd class="studio-status-path">{{ trainRemoteSegments != null ? `${trainRemoteSegments} 段 · ` : "" }}{{ trainRemotePath }}</dd>
            </div>
            <div>
              <dt>环境</dt>
              <dd>
                <span class="studio-chip" :class="engineMock ? 'studio-chip--warn' : 'studio-chip--ok'">{{ engineMock ? "引擎 Mock" : "引擎 9880" }}</span>
                <span class="studio-chip" :class="asrAvailable ? 'studio-chip--ok' : 'studio-chip--muted'">{{ asrAvailable ? "ASR 就绪" : "ASR 未就绪" }}</span>
                <span v-if="cloudTrainAvailable" class="studio-chip" :class="cloudGpuConnected ? 'studio-chip--ok' : 'studio-chip--warn'">{{ cloudGpuConnected ? "GPU 已连接" : "GPU 未验证" }}</span>
              </dd>
            </div>
          </dl>
        </RackPanel>
        <RackPanel label="日志" title="操作记录" body-class="studio-log-body">
          <div v-if="studioJobPolling" class="studio-train-active__log-hint">
            训练中 · {{ trainProgressLine || "等待远端进度…" }}
          </div>
          <div class="log-panel studio-log-panel">{{ logText }}</div>
        </RackPanel>
      </aside>
      </div>
    </PageSurface>
  </div>
</template>

<style scoped>
.studio-quota-panel {
  margin-bottom: 14px;
}

.studio-make-wrap {
  min-height: 0;
}

.studio-clone-options {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.35rem;
}

.studio-clone-option {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.55rem 0.65rem;
  border: 1px solid var(--border-muted, rgba(255, 255, 255, 0.12));
  border-radius: 6px;
  cursor: pointer;
}

.studio-clone-option--active {
  border-color: var(--accent, #c9a227);
  background: rgba(201, 162, 39, 0.06);
}

.studio-clone-option input {
  margin-right: 0.35rem;
}

.studio-clone-option__title {
  font-weight: 600;
}

.studio-clone-option__desc {
  font-size: 0.85rem;
  opacity: 0.75;
  padding-left: 1.35rem;
}

.studio-cloud-option {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
  margin-top: 0.45rem;
  cursor: pointer;
  font-size: 0.9rem;
}

.studio-cloud-option input {
  margin-top: 0.2rem;
  flex-shrink: 0;
}

.studio-cloud-option__hint {
  display: block;
  font-size: 0.82rem;
  opacity: 0.72;
  margin-top: 0.1rem;
}

.studio-cloud-option--muted {
  opacity: 0.55;
}

.studio-seg-preview {
  margin-top: 0.5rem;
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid var(--border-muted, rgba(255, 255, 255, 0.1));
  border-radius: 6px;
  padding: 0.35rem;
}

.studio-seg-preview__row {
  padding: 0.4rem 0.35rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.studio-seg-preview__row:last-child {
  border-bottom: none;
}

.studio-seg-preview__meta {
  font-size: 0.78rem;
  opacity: 0.7;
}

.studio-seg-preview__emo {
  margin-left: 0.4rem;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
  background: rgba(201, 162, 39, 0.15);
  color: #c9a227;
  font-weight: 600;
}

.studio-seg-preview__orig {
  margin: 0.15rem 0;
  font-size: 0.75rem;
  opacity: 0.65;
  line-height: 1.35;
}

.studio-seg-preview__note {
  margin: 0.15rem 0 0;
  font-size: 0.75rem;
  color: #c9a227;
  opacity: 0.85;
}

.studio-seg-preview__text {
  margin: 0.2rem 0;
  font-size: 0.88rem;
  line-height: 1.35;
}

.studio-seg-preview__audio {
  width: 100%;
  height: 32px;
  margin-top: 0.25rem;
}

.studio-log-panel {
  max-height: 280px;
  white-space: pre-wrap;
  word-break: break-word;
}

.studio-train-active__log-hint {
  font-size: 0.82rem;
  padding: 0.35rem 0.5rem;
  margin-bottom: 0.35rem;
  border-radius: 4px;
  background: rgba(201, 162, 39, 0.12);
  color: var(--color-highlight, #c4923a);
  line-height: 1.35;
}

.studio-checklist {
  margin: 0 0 0.75rem;
  padding-left: 1.15rem;
  font-size: 0.88rem;
  line-height: 1.55;
  opacity: 0.88;
}

.studio-asset-summary {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.45rem 0.55rem;
  margin-bottom: 0.65rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.04);
  font-size: 0.88rem;
}

.studio-asset-summary__ref {
  font-size: 0.82rem;
  opacity: 0.72;
  line-height: 1.35;
}

.studio-config-detail {
  margin: 0.65rem 0;
  padding: 0.55rem 0.65rem;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.12);
}

.studio-config-detail__title {
  margin: 0 0 0.4rem;
  font-size: 0.82rem;
  font-weight: 600;
  opacity: 0.85;
}

.studio-config-detail__grid {
  margin: 0;
  display: grid;
  gap: 0.35rem;
  font-size: 0.82rem;
}

.studio-config-detail__grid > div {
  display: grid;
  grid-template-columns: 4.5em 1fr;
  gap: 0.35rem;
  align-items: baseline;
}

.studio-config-detail__grid dt {
  margin: 0;
  opacity: 0.65;
}

.studio-config-detail__grid dd {
  margin: 0;
  line-height: 1.35;
  word-break: break-word;
}

.studio-phase-bar {
  display: flex;
  gap: 0.25rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
}

.studio-phase-bar__step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
  flex: 1;
  min-width: 3rem;
  opacity: 0.45;
}

.studio-phase-bar__step--active,
.studio-phase-bar__step--done {
  opacity: 1;
}

.studio-phase-bar__dot {
  width: 1.35rem;
  height: 1.35rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.studio-phase-bar__step--active .studio-phase-bar__dot {
  border-color: var(--accent, #c9a227);
  background: rgba(201, 162, 39, 0.2);
}

.studio-phase-bar__step--done .studio-phase-bar__dot {
  border-color: #3d8b5f;
  background: rgba(61, 139, 95, 0.2);
}

.studio-phase-bar__label {
  font-size: 0.72rem;
  text-align: center;
}

.studio-remote-path {
  word-break: break-all;
  font-family: var(--font-mono, monospace);
  font-size: 0.78rem;
}

.studio-version-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
  font-size: 0.88rem;
}

.studio-version-banner__mode {
  font-size: 0.78rem;
  opacity: 0.7;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
}

.studio-synth-hint {
  margin-bottom: 0.65rem;
  font-size: 0.88rem;
}

.studio-status-body {
  padding-bottom: 0.35rem;
}

.studio-status-list {
  margin: 0;
  display: grid;
  gap: 0.45rem;
  font-size: 0.84rem;
}

.studio-status-list > div {
  display: grid;
  gap: 0.1rem;
}

.studio-status-list dt {
  margin: 0;
  font-size: 0.72rem;
  opacity: 0.6;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.studio-status-list dd {
  margin: 0;
  line-height: 1.35;
}

.studio-status-muted {
  opacity: 0.65;
  font-size: 0.82rem;
}

.studio-status-path {
  font-family: var(--font-mono, monospace);
  font-size: 0.76rem;
  word-break: break-all;
}

.studio-chip {
  display: inline-block;
  font-size: 0.72rem;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  margin-right: 0.25rem;
  margin-bottom: 0.15rem;
}

.studio-chip--ok {
  background: rgba(61, 139, 95, 0.15);
  color: #3d8b5f;
}

.studio-chip--warn {
  background: rgba(196, 92, 92, 0.12);
  color: #c45c5c;
}

.studio-chip--muted {
  background: rgba(255, 255, 255, 0.06);
  opacity: 0.75;
}
</style>
