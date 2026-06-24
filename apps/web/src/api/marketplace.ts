import { apiJson } from "@/api/client";

export interface PublishEligibility {
  can_publish: boolean;
  invite_required: boolean;
  invited: boolean;
  on_waitlist: boolean;
  quality_gate: boolean;
  reason?: string | null;
  message?: string | null;
}

export interface WaitlistJoinResponse {
  on_waitlist: boolean;
  message: string;
}

export interface InviteRedeemResponse {
  invited: boolean;
  code: string;
  message: string;
}

export interface SellerAuthorizationStats {
  total_sales: number;
  active_authorizations: number;
  total_chars_used: number;
  total_chars_quota: number;
}

export interface InviteCodeSummary {
  invite_code_id: string;
  code: string;
  max_uses: number;
  used_count: number;
  note: string;
  expires_at?: string | null;
  revoked_at?: string | null;
  created_at?: string | null;
}

export const PROJECT_TYPE_OPTIONS = [
  { value: "", label: "未指定（不校验禁止领域）" },
  { value: "drama", label: "短剧 / 剧情" },
  { value: "finance", label: "金融" },
  { value: "medical", label: "医疗" },
  { value: "political", label: "政治" },
  { value: "news", label: "新闻资讯" },
] as const;

export function fetchPublishEligibility(): Promise<PublishEligibility> {
  return apiJson<PublishEligibility>("/api/v1/marketplace/publish-eligibility");
}

export function joinMarketplaceWaitlist(body: {
  contact?: string;
  note?: string;
}): Promise<WaitlistJoinResponse> {
  return apiJson<WaitlistJoinResponse>("/api/v1/marketplace/waitlist", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function redeemMarketplaceInvite(code: string): Promise<InviteRedeemResponse> {
  return apiJson<InviteRedeemResponse>("/api/v1/marketplace/invite/redeem", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export function fetchSellerAuthorizationStats(): Promise<SellerAuthorizationStats> {
  return apiJson<SellerAuthorizationStats>("/api/v1/seller/authorization-stats");
}

export function fetchAdminInviteCodes(): Promise<InviteCodeSummary[]> {
  return apiJson<InviteCodeSummary[]>("/api/v1/admin/marketplace/invite-codes");
}

export function createAdminInviteCode(body: {
  code: string;
  max_uses?: number;
  note?: string;
  expires_in_days?: number | null;
}): Promise<InviteCodeSummary> {
  return apiJson<InviteCodeSummary>("/api/v1/admin/marketplace/invite-codes", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export interface WaitlistEntrySummary {
  waitlist_id: string;
  user_id: string;
  phone: string;
  contact: string;
  note: string;
  created_at?: string | null;
}

export interface WaitlistIssueResponse {
  waitlist_id: string;
  user_id: string;
  code: string;
  message: string;
}

export function fetchAdminWaitlist(): Promise<WaitlistEntrySummary[]> {
  return apiJson<WaitlistEntrySummary[]>("/api/v1/admin/marketplace/waitlist");
}

export function issueWaitlistInvite(
  waitlistId: string,
  body?: { code?: string; expires_in_days?: number | null },
): Promise<WaitlistIssueResponse> {
  return apiJson<WaitlistIssueResponse>(
    `/api/v1/admin/marketplace/waitlist/${waitlistId}/issue-invite`,
    {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    },
  );
}
