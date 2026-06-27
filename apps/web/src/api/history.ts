import { apiJson } from "@/api/client";

export type SynthesisHistoryItem = {
  job_id: string;
  status: string;
  created_at: string;
  text_preview: string;
  voice_name?: string | null;
  voice_version_label?: string | null;
  audio_url?: string | null;
  duration_sec?: number | null;
  chars_billed?: number | null;
  error_message?: string | null;
};

export type SynthesisHistorySegment = {
  voice_version_id?: string | null;
  voice_name?: string | null;
  text: string;
  role?: string | null;
};

export type SynthesisHistoryDetail = SynthesisHistoryItem & {
  full_text: string;
  segments: SynthesisHistorySegment[];
  updated_at?: string | null;
};

export function fetchSynthesisHistory(limit = 50, status?: string) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) params.set("status", status);
  return apiJson<SynthesisHistoryItem[]>(`/api/v1/jobs?${params}`);
}

export function fetchSynthesisDetail(jobId: string) {
  return apiJson<SynthesisHistoryDetail>(`/api/v1/jobs/${jobId}/detail`);
}
