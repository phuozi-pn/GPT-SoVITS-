/** 运营后台为用户设置配额时的套餐档位（与调研草案一致，数值可单独微调）。 */
export type QuotaTier = {
  id: string;
  label: string;
  monthly_char_limit: number;
  monthly_train_limit: number;
  hint?: string;
};

export const QUOTA_TIERS: QuotaTier[] = [
  {
    id: "free",
    label: "免费",
    monthly_char_limit: 20_000,
    monthly_train_limit: 1,
    hint: "默认新用户",
  },
  {
    id: "creator",
    label: "创作者",
    monthly_char_limit: 500_000,
    monthly_train_limit: 5,
    hint: "独立 UP / 兼职配音",
  },
  {
    id: "team",
    label: "团队",
    monthly_char_limit: 3_000_000,
    monthly_train_limit: 20,
    hint: "短剧工作室",
  },
];
