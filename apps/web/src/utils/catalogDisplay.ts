import { LICENSE_TYPES } from "@/api/catalog";

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
