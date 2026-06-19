/** Public platform API base URL (no trailing slash). */
export const API_PUBLIC_BASE =
  import.meta.env.VITE_API_BASE?.replace(/\/$/, "") ?? "http://127.0.0.1:8001";

export const API_DOCS_URL = `${API_PUBLIC_BASE}/api/v1/docs`;

export const SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000";

/** Rewrite platform file URLs to same-origin paths (Vite dev proxy). */
export function resolveMediaUrl(src: string): string {
  if (!src || src.startsWith("/") || src.startsWith("blob:")) return src;
  try {
    const url = new URL(src);
    if (url.pathname.startsWith("/files/") || url.pathname.startsWith("/api/")) {
      return `${url.pathname}${url.search}`;
    }
    const isLocalApi =
      (url.hostname === "127.0.0.1" || url.hostname === "localhost") &&
      (url.port === "8001" || url.port === "");
    if (isLocalApi && url.pathname.startsWith("/files")) {
      return `${url.pathname}${url.search}`;
    }
  } catch {
    /* keep original */
  }
  return src;
}
