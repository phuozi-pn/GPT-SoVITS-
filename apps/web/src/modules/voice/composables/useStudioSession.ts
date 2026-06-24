/**
 * Studio 训练/合成任务跨页面持久化与后台轮询。
 * 切到其他页面后任务仍在服务端执行；返回 Studio 或点全局横幅可恢复进度。
 */
import { computed, ref } from "vue";
import { getJob, pollJob } from "@/api/client";
import type { JobResponse } from "@/types/api";

const WORKSPACE_KEY = "studio_workspace_v1";
const ACTIVE_JOB_KEY = "studio_active_job_v1";

export type StudioStep3Mode = "quick" | "cloud" | "import";

export interface StudioWorkspaceSnapshot {
  voiceId: string;
  voiceName: string;
  assetId: string;
  voiceVersionId: string;
  refText: string;
  refTextAuto: boolean;
  step: number;
  step3Mode: StudioStep3Mode;
  assetDurationSec: number;
  logLines: string[];
  audioUrl: string;
  lastSynthJobId: string;
}

export interface StudioActiveJobMeta {
  jobId: string;
  kind: "train" | "synth";
  label: string;
  timeoutMs: number;
  startedAt: string;
}

const jobStatus = ref("");
const isPolling = ref(false);

function loadJson<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

const activeJobMeta = ref<StudioActiveJobMeta | null>(loadJson<StudioActiveJobMeta>(ACTIVE_JOB_KEY));

let pollPromise: Promise<JobResponse> | null = null;
let pollJobId: string | null = null;
let pollOnTick: ((job: JobResponse) => void) | null = null;
let lastNotifiedStatus = "";

function saveJson(key: string, value: unknown) {
  sessionStorage.setItem(key, JSON.stringify(value));
}

export function loadStudioWorkspace(): StudioWorkspaceSnapshot | null {
  return loadJson<StudioWorkspaceSnapshot>(WORKSPACE_KEY);
}

export function saveStudioWorkspace(snapshot: StudioWorkspaceSnapshot) {
  saveJson(WORKSPACE_KEY, {
    ...snapshot,
    logLines: snapshot.logLines.slice(-100),
  });
}

export function loadStudioActiveJob(): StudioActiveJobMeta | null {
  return activeJobMeta.value ?? loadJson<StudioActiveJobMeta>(ACTIVE_JOB_KEY);
}

export function clearStudioActiveJob() {
  sessionStorage.removeItem(ACTIVE_JOB_KEY);
  activeJobMeta.value = null;
  pollPromise = null;
  pollJobId = null;
  pollOnTick = null;
  lastNotifiedStatus = "";
  isPolling.value = false;
}

function notifyTicks(job: JobResponse) {
  if (job.status !== lastNotifiedStatus) {
    lastNotifiedStatus = job.status;
    jobStatus.value = job.status;
  }
  pollOnTick?.(job);
}

function startPoll(meta: StudioActiveJobMeta, onTick?: (job: JobResponse) => void): Promise<JobResponse> {
  if (pollPromise && pollJobId === meta.jobId) {
    if (onTick) pollOnTick = onTick;
    return pollPromise;
  }
  pollJobId = meta.jobId;
  isPolling.value = true;
  activeJobMeta.value = meta;
  pollOnTick = onTick ?? null;
  lastNotifiedStatus = "";
  saveJson(ACTIVE_JOB_KEY, meta);
  pollPromise = pollJob(
    meta.jobId,
    (job) => notifyTicks(job),
    meta.timeoutMs,
  )
    .finally(() => {
      isPolling.value = false;
      pollPromise = null;
      pollJobId = null;
      clearStudioActiveJob();
    });
  return pollPromise;
}

/** 启动或加入后台轮询（同一 jobId 复用 Promise）。 */
export function followStudioJob(
  meta: StudioActiveJobMeta,
  workspace?: StudioWorkspaceSnapshot,
  onTick?: (job: JobResponse) => void,
): Promise<JobResponse> {
  if (workspace) saveStudioWorkspace(workspace);
  return startPoll(meta, onTick);
}

/** 训练已完成、工作区已在步骤 ④ 时，丢弃过期的 train 任务标记，避免阻塞合成。 */
export async function discardStaleTrainJob(workspace: StudioWorkspaceSnapshot | null): Promise<void> {
  const meta = loadStudioActiveJob();
  if (!meta || meta.kind !== "train") return;
  if (!workspace?.voiceVersionId || workspace.step < 4) return;
  clearStudioActiveJob();
}

/** 页面重新进入时：若任务仍在进行则继续轮询，若已结束则拉一次终态。 */
export async function resumeStudioJobIfNeeded(
  onTick?: (job: JobResponse) => void,
): Promise<JobResponse | null> {
  const meta = loadStudioActiveJob();
  if (!meta) return null;
  if (pollPromise && pollJobId === meta.jobId) {
    if (onTick) pollOnTick = onTick;
    return pollPromise;
  }
  const current = await getJob(meta.jobId);
  notifyTicks(current);
  if (current.status === "succeeded" || current.status === "failed") {
    clearStudioActiveJob();
    return current;
  }
  return startPoll(meta, onTick);
}

export function useStudioJobBanner() {
  const showBanner = computed(() => Boolean(activeJobMeta.value) && isPolling.value);
  return { activeJob: activeJobMeta, showBanner, jobStatus, isPolling };
}

export { isPolling, jobStatus };

export function appendStudioLog(snapshot: StudioWorkspaceSnapshot, line: string): StudioWorkspaceSnapshot {
  const ts = new Date().toLocaleTimeString();
  const next = {
    ...snapshot,
    logLines: [...snapshot.logLines, `[${ts}] ${line}`].slice(-100),
  };
  saveStudioWorkspace(next);
  return next;
}
