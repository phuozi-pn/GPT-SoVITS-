import { buildAuthHeaders } from "@/api/client";
import { resolveMediaUrl } from "@/config";

const blobCache = new Map<string, string>();

function needsAuthFetch(src: string): boolean {
  const media = resolveMediaUrl(src);
  return media.startsWith("/api/");
}

export async function loadPlayableMediaUrl(src: string): Promise<string> {
  if (!src) return "";
  const media = resolveMediaUrl(src);
  if (!needsAuthFetch(src)) return media;

  const cached = blobCache.get(media);
  if (cached) return cached;

  const res = await fetch(media, { headers: buildAuthHeaders() });
  if (!res.ok) {
    throw new Error(`音频加载失败 (${res.status})`);
  }
  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  blobCache.set(media, objectUrl);
  return objectUrl;
}

export function revokePlayableMediaUrl(src: string) {
  if (!src) return;
  const media = resolveMediaUrl(src);
  const objectUrl = blobCache.get(media);
  if (!objectUrl) return;
  URL.revokeObjectURL(objectUrl);
  blobCache.delete(media);
}
