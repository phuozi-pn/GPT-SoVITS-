import { apiJson } from "./client";

export interface CloudGpuProfile {
  ssh_host: string;
  ssh_port: number;
  ssh_user: string;
  auth_type: string;
  has_credential: boolean;
  remote_engine_root: string;
  remote_platform_root: string;
  remote_work_dir: string;
  last_tested_at?: string | null;
  last_test_ok?: boolean | null;
}

export interface CloudGpuProfileSaveBody {
  ssh_host: string;
  ssh_port: number;
  ssh_user: string;
  password: string;
  remote_engine_root: string;
  remote_platform_root: string;
  remote_work_dir: string;
}

export interface CloudGpuTestResult {
  ok: boolean;
  message: string;
  checks: { name: string; ok: boolean; detail?: string }[];
}

export async function fetchCloudGpuProfile() {
  return apiJson<CloudGpuProfile | null>("/api/v1/cloud-gpu/profile");
}

export async function saveCloudGpuProfile(body: CloudGpuProfileSaveBody) {
  return apiJson<CloudGpuProfile>("/api/v1/cloud-gpu/profile", {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function testCloudGpuConnection(body: Partial<CloudGpuProfileSaveBody>) {
  return apiJson<CloudGpuTestResult>("/api/v1/cloud-gpu/profile/test", {
    method: "POST",
    body: JSON.stringify({
      ssh_host: body.ssh_host,
      ssh_port: body.ssh_port,
      ssh_user: body.ssh_user,
      password: body.password,
      remote_engine_root: body.remote_engine_root,
      remote_platform_root: body.remote_platform_root,
    }),
  });
}

export interface DatasetPreviewSegment {
  index: number;
  name: string;
  duration_sec: number;
  text: string;
  audio_url: string;
  text_original?: string | null;
  emotion?: string | null;
  emotion_label?: string | null;
  emotion_strength?: number | null;
  notes?: string | null;
}

export interface DatasetPreviewResult {
  asset_id: string;
  source_duration_sec: number;
  mode: string;
  segment_count: number;
  use_asr: boolean;
  segments: DatasetPreviewSegment[];
  infer_ref_text: string;
  enrich_mode?: string;
}

export async function previewCloudDataset(
  assetId: string,
  useAsr?: boolean,
  useLlmEnrich?: boolean,
) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 10 * 60 * 1000);
  try {
    return await apiJson<DatasetPreviewResult>("/api/v1/cloud-gpu/dataset-preview", {
      method: "POST",
      body: JSON.stringify({
        asset_id: assetId,
        ...(useAsr !== undefined ? { use_asr: useAsr } : {}),
        ...(useLlmEnrich !== undefined ? { use_llm_enrich: useLlmEnrich } : { use_llm_enrich: true }),
      }),
      signal: controller.signal,
    });
  } finally {
    window.clearTimeout(timer);
  }
}
