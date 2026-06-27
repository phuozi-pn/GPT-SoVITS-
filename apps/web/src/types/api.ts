/**
 * API 响应 / 请求类型定义
 *
 * 从 api/client.ts 提取，避免类型定义与 HTTP 逻辑耦合。
 */

// ── 认证 ──────────────────────────────────────────────────

export interface QuotaSummary {
  chars_used: number;
  chars_remaining: number;
  monthly_char_limit: number;
  wallet_token_balance?: number;
  total_tokens_remaining?: number;
  trainings_used: number;
  trainings_remaining: number;
  monthly_train_limit: number;
  reset_at?: string;
}

export interface LoginResponse {
  access_token: string;
  user: { user_id: string; phone?: string | null; email?: string | null };
  quota: QuotaSummary | null;
}

// ── Job ───────────────────────────────────────────────────

export interface JobResponse {
  job_id: string;
  job_type: string;
  status: string;
  trace_id?: string | null;
  owner_user_id?: string | null;
  error_message?: string | null;
  audio_url?: string | null;
  voice_version_id?: string | null;
  line_count?: number | null;
  succeeded_count?: number | null;
  failed_count?: number | null;
  zip_url?: string | null;
  train_gpt_epochs?: number | null;
  train_sovits_epochs?: number | null;
  train_elapsed_sec?: number | null;
  train_dataset_segments?: number | null;
  train_remote_work_dir?: string | null;
  train_remote_dataset_path?: string | null;
  train_progress_phase?: string | null;
  train_progress_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  text_preview?: string | null;
  full_text?: string | null;
  voice_name?: string | null;
  voice_version_label?: string | null;
  duration_sec?: number | null;
  chars_billed?: number | null;
}

// ── 合成 ──────────────────────────────────────────────────

export type SynthesisSegmentBody = {
  voice_version_id: string;
  text: string;
  speed_factor?: number;
  temperature?: number;
  top_p?: number;
  pitch_factor?: number;
  emotion?: string | null;
  emotion_strength?: number;
  pause_duration?: number;
};

export type SynthesisBody = {
  voice_version_id?: string;
  text?: string;
  format?: "wav" | "mp3";
  ai_disclosure_ack?: boolean;
  temperature?: number;
  speed_factor?: number;
  top_p?: number;
  emotion?: string | null;
  emotion_strength?: number;
  project_type?: string | null;
  segments?: SynthesisSegmentBody[];
};

// ── 水印 ──────────────────────────────────────────────────

export interface WatermarkDetectResult {
  watermark_detected: boolean;
  message?: string;
  user_id?: string;
  voice_id?: string;
  job_id?: string;
  timestamp?: string;
}

// ── 情感分析 ──────────────────────────────────────────────

export interface EmotionAnalyzeResult {
  emotion: string;
  emotion_label: string;
  strength: number;
  text_preview: string;
}

export interface EmotionBatchItem {
  index: number;
  emotion: string;
  emotion_label: string;
  strength: number;
}

export interface EmotionBatchResult {
  results: EmotionBatchItem[];
}

// ── 音频指纹 ──────────────────────────────────────────────

export interface FingerprintEnrollResponse {
  fingerprint_id: string;
  hash_count: number;
  enrolled_at: string;
}

export interface FingerprintMatch {
  fingerprint_id: string;
  job_id: string;
  user_id?: string | null;
  voice_id?: string | null;
  enrolled_at: string;
  similarity: number;
}

export interface FingerprintSearchResponse {
  matches: FingerprintMatch[];
  search_duration_ms: number;
}

export interface FingerprintStatusResponse {
  total_enrolled: number;
  engine: string;
}
