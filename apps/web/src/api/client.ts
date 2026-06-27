/**
 * 统一 HTTP 客户端
 *
 * 职责：认证头注入、Trace-Id 管理、错误解析、通用 JSON 请求封装。
 * 类型定义已迁移至 src/types/api.ts，此处 re-export 保持向后兼容。
 */

// ── Re-export 类型（向后兼容） ───────────────────────────

export type {
  QuotaSummary,
  LoginResponse,
  JobResponse,
  SynthesisSegmentBody,
  SynthesisBody,
  WatermarkDetectResult,
  EmotionAnalyzeResult,
  EmotionBatchItem,
  EmotionBatchResult,
  FingerprintEnrollResponse,
  FingerprintMatch,
  FingerprintSearchResponse,
  FingerprintStatusResponse,
} from "@/types/api";

// ── 错误类型 ─────────────────────────────────────────────

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

// ── 内部工具 ─────────────────────────────────────────────

import { _requestEnd, _requestStart } from "@/composables/useRequestLoading";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export function buildAuthHeaders(): HeadersInit {
  const token = localStorage.getItem("access_token");
  const headers: Record<string, string> = {};
  let traceId = sessionStorage.getItem("trace_id");
  if (!traceId) {
    traceId = crypto.randomUUID();
    sessionStorage.setItem("trace_id", traceId);
  }
  headers["X-Trace-Id"] = traceId;
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  } else if (localStorage.getItem("dev_mode") === "1") {
    headers["X-User-Id"] =
      localStorage.getItem("dev_user_id") ?? "00000000-0000-0000-0000-000000000001";
  }
  return headers;
}

async function parseError(res: Response): Promise<ApiError> {
  let code = "HTTP_ERROR";
  let message = res.statusText;
  try {
    const body = await res.json();
    // 优先读取标准格式 { code, message }
    if (body.code && body.message) {
      code = body.code;
      message = body.message;
    } else if (body.detail?.code) {
      code = body.detail.code;
      message = body.detail.message ?? message;
    } else if (body.error?.code) {
      // 兼容旧版限流格式
      code = body.error.code;
      message = body.error.message ?? message;
    } else if (Array.isArray(body.detail)) {
      const first = body.detail[0];
      code = first?.type ?? "VALIDATION_ERROR";
      message = first?.msg ?? message;
      const field = (first?.loc as unknown[] | undefined)
        ?.filter((part) => part !== "body")
        .join(".");
      if (field) {
        message = `${field}: ${message}`;
      }
    } else if (typeof body.detail === "string") {
      message = body.detail;
    } else if (body.message) {
      message = body.message;
    }
  } catch {
    /* ignore */
  }
  return new ApiError(res.status, code, message);
}

// ── 公共 API ─────────────────────────────────────────────

export async function apiJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  _requestStart();
  try {
    const headers = new Headers(init.headers);
    if (!headers.has("Content-Type") && init.body && !(init.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }
    for (const [k, v] of Object.entries(buildAuthHeaders())) {
      headers.set(k, v);
    }
    const hadToken = Boolean(localStorage.getItem("access_token"));
    const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
    if (!res.ok) {
      if (res.status === 401 && hadToken && !path.startsWith("/api/v1/auth/")) {
        localStorage.removeItem("access_token");
      }
      throw await parseError(res);
    }
    if (res.status === 204) {
      return undefined as T;
    }
    return (await res.json()) as T;
  } finally {
    _requestEnd();
  }
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

// ── 业务 API 函数 ────────────────────────────────────────

import type {
  LoginResponse,
  QuotaSummary,
  JobResponse,
  SynthesisBody,
  WatermarkDetectResult,
  EmotionAnalyzeResult,
  EmotionBatchResult,
  FingerprintEnrollResponse,
  FingerprintSearchResponse,
  FingerprintStatusResponse,
} from "@/types/api";

export async function sendSms(phone: string) {
  return apiJson<{ mock_code?: string | null; message: string }>("/api/v1/auth/sms/send", {
    method: "POST",
    body: JSON.stringify({ phone }),
  });
}

export async function sendEmailCode(email: string) {
  return apiJson<{ mock_code?: string | null; message: string }>("/api/v1/auth/email/send", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function login(phone: string, code: string) {
  return apiJson<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ phone, code }),
  });
}

export async function loginWithEmail(email: string, code: string) {
  return apiJson<LoginResponse>("/api/v1/auth/email/login", {
    method: "POST",
    body: JSON.stringify({ email, code }),
  });
}

export async function fetchQuota() {
  return apiJson<QuotaSummary>("/api/v1/usage/quota");
}

export interface PlatformCapabilities {
  train_mode: string;
  train_mode_label: string;
  engine_mock: boolean;
  engine_tts_url: string;
  train_mock: boolean;
  kyc_required: boolean;
  kyc_mock: boolean;
  asr_enabled: boolean;
  asr_available: boolean;
  cloud_train_configured: boolean;
  cloud_train_available: boolean;
  cloud_train_issues: string[];
  engine_train_root_ready: boolean;
  weight_import_available: boolean;
  quick_clone_available: boolean;
  cloud_train_self_service: boolean;
  cloud_train_user_connected: boolean;
  cloud_train_local_dataset_prep_default: boolean;
  cloud_train_use_asr_default: boolean;
  cloud_train_gpt_epochs: number;
  cloud_train_sovits_epochs: number;
  cloud_train_epoch_label: string;
}

export async function fetchPlatformCapabilities() {
  return apiJson<PlatformCapabilities>("/api/v1/platform/capabilities");
}

export async function createVoice(name: string) {
  return apiJson<{ voice_id: string; name: string }>("/api/v1/voices", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function createConsent(voiceId: string) {
  return apiJson<{ consent_id: string; status: string }>("/api/v1/consents", {
    method: "POST",
    body: JSON.stringify({ voice_id: voiceId }),
  });
}

export async function uploadAsset(voiceId: string, file: File, refText?: string) {
  const form = new FormData();
  form.append("voice_id", voiceId);
  if (refText?.trim()) form.append("ref_text", refText.trim());
  form.append("audio_file", file);
  return apiJson<{
    asset_id: string;
    qc_passed: boolean;
    qc_result?: {
      ref_text?: string | null;
      ref_text_auto?: boolean;
      asr_provider?: string | null;
      audio_enhanced?: boolean;
      enhance_note?: string | null;
      issues?: { code?: string; message: string }[];
    };
  }>("/api/v1/voices/assets", { method: "POST", body: form });
}

export async function confirmAsset(assetId: string) {
  return apiJson<{ asset_id: string; locked: boolean }>(
    `/api/v1/voices/assets/${assetId}/confirm`,
    { method: "POST" },
  );
}

export async function startTrain(
  voiceId: string,
  voiceAssetId: string,
  opts?: {
    trainBackend?: "auto" | "quick" | "engine" | "cloud";
    cloudLocalDatasetPrep?: boolean;
    cloudUseAsr?: boolean;
  },
) {
  return apiJson<{ job_id: string; status: string }>(`/api/v1/voices/${voiceId}/train`, {
    method: "POST",
    body: JSON.stringify({
      voice_asset_id: voiceAssetId,
      model_tag: "gsv-v2pro-20250606",
      ...(opts?.trainBackend && opts.trainBackend !== "auto"
        ? { train_backend: opts.trainBackend }
        : {}),
      ...(opts?.trainBackend === "cloud" && opts.cloudLocalDatasetPrep !== undefined
        ? { cloud_local_dataset_prep: opts.cloudLocalDatasetPrep }
        : {}),
      ...(opts?.trainBackend === "cloud" && opts.cloudUseAsr !== undefined
        ? { cloud_use_asr: opts.cloudUseAsr }
        : {}),
    }),
  });
}

export interface ImportWeightsUploadOpts {
  voiceName: string;
  refText: string;
  voiceId?: string;
  label?: string;
  consentId?: string;
  voiceAssetId?: string;
}

export async function importEngineWeightsUpload(
  gpt: File,
  sovits: File,
  refAudio: File,
  opts: ImportWeightsUploadOpts,
) {
  const form = new FormData();
  form.append("gpt_weights", gpt);
  form.append("sovits_weights", sovits);
  form.append("ref_audio", refAudio);
  form.append("voice_name", opts.voiceName);
  form.append("ref_text", opts.refText);
  if (opts.voiceId) form.append("voice_id", opts.voiceId);
  if (opts.label) form.append("label", opts.label);
  if (opts.consentId) form.append("consent_id", opts.consentId);
  if (opts.voiceAssetId) form.append("voice_asset_id", opts.voiceAssetId);
  return apiJson<{
    voice_version_id: string;
    voice_id: string;
    voice_name: string;
    version: number;
    imported?: boolean;
  }>("/api/v1/voices/import-weights/upload", {
    method: "POST",
    body: form,
  });
}

export async function synthesize(
  body: SynthesisBody,
  aiDisclosureAck = true,
) {
  return apiJson<{ job_id: string; status: string }>("/api/v1/synthesis", {
    method: "POST",
    body: JSON.stringify({
      format: "wav",
      ...body,
      ai_disclosure_ack: body.ai_disclosure_ack ?? aiDisclosureAck,
    }),
  });
}

/** @deprecated Use synthesize(body) with full options */
export async function synthesizeSimple(
  voiceVersionId: string,
  text: string,
  aiDisclosureAck = true,
  opts?: { temperature?: number; speed_factor?: number; top_p?: number },
) {
  return synthesize(
    {
      voice_version_id: voiceVersionId,
      text,
      temperature: opts?.temperature,
      speed_factor: opts?.speed_factor,
      top_p: opts?.top_p,
    },
    aiDisclosureAck,
  );
}

export function exportDownloadUrl(jobId: string): string {
  return `${API_BASE}/api/v1/exports/${jobId}/download`;
}

export async function getJob(jobId: string) {
  return apiJson<JobResponse>(`/api/v1/jobs/${jobId}`);
}

export async function pollJob(
  jobId: string,
  onTick?: (job: JobResponse) => void,
  timeoutMs = 600_000,
): Promise<JobResponse> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const job = await getJob(jobId);
    onTick?.(job);
    if (job.status === "succeeded" || job.status === "failed") {
      return job;
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error("任务超时，请稍后在任务 ID 处手动查询");
}

/** Upload a WAV file for watermark detection */
export async function detectWatermark(file: File): Promise<WatermarkDetectResult> {
  const form = new FormData();
  form.append("file", file);
  return apiJson<WatermarkDetectResult>("/api/v1/watermark/detect", {
    method: "POST",
    body: form,
  });
}

// ── REQ-027: Auto emotion detection ──────────────────────

/** Analyze a single text for auto emotion detection */
export async function analyzeEmotion(text: string): Promise<EmotionAnalyzeResult> {
  return apiJson<EmotionAnalyzeResult>("/api/v1/emotion/analyze", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

/** Analyze multiple text segments for emotion in one request */
export async function analyzeEmotionBatch(texts: string[]): Promise<EmotionBatchResult> {
  return apiJson<EmotionBatchResult>("/api/v1/emotion/analyze-batch", {
    method: "POST",
    body: JSON.stringify({ texts }),
  });
}

// ── REQ-025: Audio fingerprint ───────────────────────────

/** Enroll an audio fingerprint by uploading a WAV file */
export async function enrollFingerprint(file: File, jobId: string): Promise<FingerprintEnrollResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("job_id", jobId);
  return apiJson<FingerprintEnrollResponse>("/api/v1/fingerprint/enroll-audio", {
    method: "POST",
    body: form,
  });
}

/** Search for matching fingerprints by uploading a WAV file */
export async function searchFingerprint(
  file: File,
  threshold = 0.05,
  maxResults = 10,
): Promise<FingerprintSearchResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("threshold", String(threshold));
  form.append("max_results", String(maxResults));
  return apiJson<FingerprintSearchResponse>("/api/v1/fingerprint/search", {
    method: "POST",
    body: form,
  });
}

/** Get fingerprint store status */
export async function fingerprintStatus(): Promise<FingerprintStatusResponse> {
  return apiJson<FingerprintStatusResponse>("/api/v1/fingerprint/status");
}

// ── Batch Lines (行级状态) ──────────────────────────────

export interface BatchLineItem {
  line_index: number;
  role: string;
  text: string;
  voice_version_id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  audio_url: string | null;
  duration_sec: number | null;
  export_compliant: boolean;
  label_type: string | null;
  labeled_at: string | null;
  error_code: string | null;
  error_message: string | null;
}

export interface BatchLinesData {
  job_id: string;
  lines: BatchLineItem[];
  total: number;
  succeeded: number;
  failed: number;
  queued: number;
  running: number;
}

export async function getBatchLines(jobId: string): Promise<BatchLinesData> {
  return apiJson<BatchLinesData>(`/api/v1/jobs/${jobId}/lines`);
}

export async function retryBatchLines(
  jobId: string,
  lineIndices: number[],
): Promise<BatchLinesData> {
  return apiJson<BatchLinesData>(`/api/v1/jobs/${jobId}/lines/retry`, {
    method: "POST",
    body: JSON.stringify({ line_indices: lineIndices }),
  });
}
