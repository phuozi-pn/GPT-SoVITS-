import { apiJson } from "./client";
import type { CatalogEntry } from "./catalog";

export interface FeaturedCreatorSummary {
  user_id: string;
  display_name: string;
  bio: string;
  avatar_url?: string | null;
  published_count: number;
  featured_voice_count: number;
  spotlight_voice: CatalogEntry | null;
}

export async function fetchPublicCatalog(opts?: {
  featured?: boolean;
  tags?: string[];
  owner?: string;
  page?: number;
  page_size?: number;
}) {
  const params = new URLSearchParams();
  if (opts?.featured) params.set("featured", "true");
  if (opts?.tags?.length) params.set("tags", opts.tags.join(","));
  if (opts?.owner) params.set("owner", opts.owner);
  if (opts?.page) params.set("page", String(opts.page));
  if (opts?.page_size) params.set("page_size", String(opts.page_size));
  const q = params.toString();
  return apiJson<CatalogEntry[]>(`/api/v1/public/catalog${q ? `?${q}` : ""}`);
}

export async function fetchFeaturedCreators(limit = 12) {
  return apiJson<FeaturedCreatorSummary[]>(`/api/v1/public/creators?limit=${limit}`);
}
