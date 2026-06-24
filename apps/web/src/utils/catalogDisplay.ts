import type { CatalogEntry } from "@/api/catalog";
import { LICENSE_TYPES } from "@/api/catalog";

export type CatalogAccessTone = "ok" | "warn" | "muted";

export function catalogAccessStatus(
  entry: Pick<CatalogEntry, "can_use" | "purchased" | "price_cents" | "owner_user_id">,
  viewerUserId: string,
): { label: string; tone: CatalogAccessTone } {
  if (entry.owner_user_id === viewerUserId) {
    return { label: "我的音色", tone: "muted" };
  }
  if (entry.purchased) {
    return { label: "已购买", tone: "ok" };
  }
  if (!entry.can_use && entry.price_cents > 0) {
    return { label: "需购买", tone: "warn" };
  }
  if (entry.can_use && entry.price_cents === 0) {
    return { label: "免费可用", tone: "ok" };
  }
  if (entry.can_use) {
    return { label: "已授权", tone: "ok" };
  }
  return { label: "不可用", tone: "warn" };
}

export function catalogAccessPillClass(tone: CatalogAccessTone): string {
  if (tone === "warn") return "pill pill--warn";
  if (tone === "muted") return "pill pill--muted";
  return "pill pill--ok";
}

export function parseCatalogTags(raw: string): string[] {
  return raw
    .split(/[,，]/)
    .map((t) => t.trim())
    .filter(Boolean)
    .slice(0, 10);
}

export function licenseLabel(id: string): string {
  return LICENSE_TYPES.find((t) => t.id === id)?.label ?? id;
}

export function catalogStatusLabel(status: string): string {
  if (status === "pending") return "待审核";
  if (status === "published") return "已上架";
  if (status === "rejected") return "已驳回";
  return status;
}

export function avatarInitial(title: string): string {
  return title.trim().charAt(0) || "音";
}

export function shortUserId(id: string): string {
  return id.length > 8 ? `${id.slice(0, 8)}…` : id;
}
