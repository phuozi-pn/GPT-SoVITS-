import { apiJson } from "./client";

export interface QualityReport {
  voice_version_id: string;
  similarity_score: number;
  quality_pass: boolean;
  threshold: number;
  eval_sentence: string;
  ref_audio_url?: string | null;
  synth_audio_url?: string | null;
  method: string;
  ab_vote_count: number;
  ref_pick_rate?: number | null;
}

export interface AbTrial {
  voice_version_id: string;
  audio_a_url: string;
  audio_b_url: string;
  slot_a_kind: string;
  slot_b_kind: string;
  instruction: string;
}

export interface AbVoteResult {
  vote_id: string;
  picked_kind: string;
  correct: boolean;
  message: string;
}

export async function fetchQualityReport(voiceVersionId: string) {
  return apiJson<QualityReport>(`/api/v1/voice-versions/${voiceVersionId}/quality`);
}

export async function evaluateQuality(voiceVersionId: string) {
  return apiJson<QualityReport>(`/api/v1/voice-versions/${voiceVersionId}/quality/evaluate`, {
    method: "POST",
  });
}

export async function fetchAbTrial(voiceVersionId: string) {
  return apiJson<AbTrial>(`/api/v1/voice-versions/${voiceVersionId}/ab-trial`);
}

export async function submitAbVote(
  voiceVersionId: string,
  body: {
    pick_slot: "a" | "b";
    slot_a_kind: string;
    slot_b_kind: string;
    score?: number;
  },
) {
  return apiJson<AbVoteResult>(`/api/v1/voice-versions/${voiceVersionId}/ab-vote`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function authorizationCertificatePdfUrl(authorizationId: string): string {
  const base = import.meta.env.VITE_API_BASE ?? "";
  return `${base}/api/v1/authorizations/${authorizationId}/certificate.pdf`;
}
