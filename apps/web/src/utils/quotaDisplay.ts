import type { QuotaSummary } from "@/types/api";

export type QuotaUsageTone = "ok" | "warn" | "danger";

/** 产品向 Token 单位标签（计量口径见模块 A：1 Token = 1 Unicode 码点） */
export const QUOTA_TOKEN_UNIT = "Token";

export function formatPriceYuan(cents: number): string {
  return `¥${(cents / 100).toFixed(cents % 100 === 0 ? 0 : 2)}`;
}

export function ledgerKindLabel(kind: string): string {
  if (kind === "purchase") return "购买充值";
  if (kind === "synthesis_debit") return "合成扣减";
  return kind;
}

/** 将 Token 数格式化为产品向文案（万 / 千 / 原值） */
export function formatTokenVolume(value: number): string {
  const n = Math.max(0, Math.round(value));
  if (n >= 10_000) {
    const wan = n / 10_000;
    const digits = wan >= 100 ? 0 : wan >= 10 ? 1 : 2;
    return `${wan.toFixed(digits).replace(/\.0+$/, "")} 万`;
  }
  if (n >= 1_000) {
    return `${(n / 1_000).toFixed(1).replace(/\.0$/, "")} 千`;
  }
  return n.toLocaleString("zh-CN");
}

export function formatTokenVolumeWithUnit(value: number): string {
  return `${formatTokenVolume(value)} ${QUOTA_TOKEN_UNIT}`;
}

export function usagePercent(used: number, limit: number): number {
  if (limit <= 0) return used > 0 ? 100 : 0;
  return Math.min(100, Math.round((used / limit) * 100));
}

export function usageTone(used: number, limit: number): QuotaUsageTone {
  const pct = limit > 0 ? used / limit : 0;
  if (pct >= 1) return "danger";
  if (pct >= 0.8) return "warn";
  return "ok";
}

export function formatResetLabel(resetAt?: string | null): string {
  if (!resetAt) return "下月 1 日重置";
  const date = new Date(resetAt);
  if (Number.isNaN(date.getTime())) return "下月 1 日重置";
  return `${date.toLocaleDateString("zh-CN", { month: "long", day: "numeric" })} 重置`;
}

export type QuotaMeterModel = {
  key: string;
  label: string;
  unit: string;
  used: number;
  limit: number;
  remaining: number;
  percent: number;
  tone: QuotaUsageTone;
  usedLabel: string;
  limitLabel: string;
  remainingLabel: string;
};

export function buildQuotaMeters(quota: QuotaSummary): QuotaMeterModel[] {
  return [
    {
      key: "chars",
      label: "TTS Token",
      unit: QUOTA_TOKEN_UNIT,
      used: quota.chars_used,
      limit: quota.monthly_char_limit,
      remaining: quota.chars_remaining,
      percent: usagePercent(quota.chars_used, quota.monthly_char_limit),
      tone: usageTone(quota.chars_used, quota.monthly_char_limit),
      usedLabel: formatTokenVolumeWithUnit(quota.chars_used),
      limitLabel: formatTokenVolumeWithUnit(quota.monthly_char_limit),
      remainingLabel: formatTokenVolumeWithUnit(quota.chars_remaining),
    },
    {
      key: "train",
      label: "模型训练",
      unit: "次",
      used: quota.trainings_used,
      limit: quota.monthly_train_limit,
      remaining: quota.trainings_remaining,
      percent: usagePercent(quota.trainings_used, quota.monthly_train_limit),
      tone: usageTone(quota.trainings_used, quota.monthly_train_limit),
      usedLabel: `${quota.trainings_used} 次`,
      limitLabel: `${quota.monthly_train_limit} 次`,
      remainingLabel: `${quota.trainings_remaining} 次`,
    },
  ];
}
