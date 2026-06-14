import { apiJson } from "./client";

export interface CatalogEntry {
  catalog_id: string;
  voice_version_id: string;
  voice_id: string;
  voice_name: string;
  title: string;
  description: string;
  tags: string[];
  featured: boolean;
  owner_user_id: string;
  can_use: boolean;
}

export async function fetchCatalog(featured = false) {
  const q = featured ? "?featured=true" : "";
  return apiJson<CatalogEntry[]>(`/api/v1/catalog/voices${q}`);
}

export async function publishToCatalog(body: {
  voice_version_id: string;
  title: string;
  description?: string;
  tags?: string[];
  featured?: boolean;
}) {
  return apiJson<CatalogEntry>("/api/v1/catalog/voices", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function createVoiceGrant(voiceId: string, granteeUserId: string) {
  return apiJson<{ grant_id: string }>(`/api/v1/voices/${voiceId}/grants`, {
    method: "POST",
    body: JSON.stringify({ grantee_user_id: granteeUserId }),
  });
}
