import { apiJson } from "./client";
import type { CatalogEntry } from "./catalog";
import type { VoiceVersionSummary } from "./library";
import { versionDefaultDisplayName } from "@/utils/voiceOriginDisplay";

export interface VoiceVersionManageSummary extends VoiceVersionSummary {
  catalog_id?: string | null;
  catalog_status?: string | null;
  catalog_title?: string | null;
  catalog_cover_image_url?: string | null;
  catalog_tags?: string[];
  can_unpublish?: boolean;
  can_delete: boolean;
  delete_block_reason?: string | null;
}

export interface VoiceAssetManageSummary {
  asset_id: string;
  voice_id: string;
  storage_uri: string;
  locked: boolean;
  qc_passed: boolean;
  qc_status?: string | null;
  duration_sec?: number | null;
  preview_audio_url?: string | null;
  created_at?: string | null;
}

export interface VoiceConsentManageSummary {
  consent_id: string;
  voice_id: string;
  status: string;
  approved_at?: string | null;
  expires_at?: string | null;
  created_at?: string | null;
}

export interface VoiceManageSummary {
  voice_id: string;
  name: string;
  version_count: number;
  latest_version_id?: string | null;
  versions?: VoiceVersionManageSummary[] | null;
  assets?: VoiceAssetManageSummary[] | null;
  consents?: VoiceConsentManageSummary[] | null;
}

export async function fetchMyVoicesDetail() {
  return apiJson<VoiceManageSummary[]>("/api/v1/voices?detail=true");
}

export async function updateVoiceName(voiceId: string, name: string) {
  return apiJson<VoiceManageSummary>(`/api/v1/voices/${voiceId}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export async function updateVoiceVersion(
  voiceVersionId: string,
  body: { label?: string; ref_text?: string },
) {
  return apiJson<VoiceVersionSummary>(`/api/v1/voice-versions/${voiceVersionId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteVoiceVersion(voiceVersionId: string) {
  return apiJson<void>(`/api/v1/voice-versions/${voiceVersionId}`, { method: "DELETE" });
}

export async function deleteVoice(voiceId: string) {
  return apiJson<void>(`/api/v1/voices/${voiceId}`, { method: "DELETE" });
}

export async function unpublishCatalogEntry(catalogId: string) {
  return apiJson<CatalogEntry>(`/api/v1/catalog/voices/${catalogId}/unpublish`, {
    method: "POST",
  });
}

export function catalogStatusLabel(status?: string | null) {
  if (!status) return null;
  if (status === "pending") return "审核中";
  if (status === "published") return "已上架";
  if (status === "rejected") return "已驳回";
  if (status === "takedown") return "已下架";
  return status;
}

export function consentStatusLabel(status: string) {
  if (status === "approved") return "已通过";
  if (status === "pending") return "待审核";
  if (status === "rejected") return "已驳回";
  return status;
}

export function qcStatusLabel(status?: string | null, qcPassed?: boolean) {
  if (status === "passed" || qcPassed) return "质检通过";
  if (status === "failed") return "质检未通过";
  if (status) return status;
  return qcPassed ? "已通过" : "待质检";
}

export function formatDuration(sec?: number | null) {
  if (sec == null) return "—";
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function versionDisplayName(v: VoiceVersionManageSummary) {
  return versionDefaultDisplayName(v);
}
