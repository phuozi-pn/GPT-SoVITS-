import { apiJson, ApiError } from "./client";

export interface CatalogEntry {
  catalog_id: string;
  voice_version_id: string;
  voice_id: string;
  voice_name: string;
  title: string;
  description: string;
  tags: string[];
  featured: boolean;
  status: string;
  demo_text?: string;
  demo_audio_url?: string | null;
  demo_job_id?: string | null;
  owner_user_id: string;
  can_use: boolean;
  license_type: string;
  price_cents: number;
  billing_unit: string;
  included_chars: number;
  prohibited_domains: string[];
  policy_version: number;
  purchased: boolean;
}

export const LICENSE_TYPES = [
  { id: "personal_non_commercial", label: "个人非商用" },
  { id: "commercial_standard", label: "商用标准" },
  { id: "commercial_exclusive", label: "商用独家" },
] as const;

export const PROHIBITED_DOMAIN_OPTIONS = [
  "finance",
  "medical",
  "political",
  "news",
] as const;

export interface Authorization {
  authorization_id: string;
  catalog_id: string;
  voice_version_id: string;
  voice_id: string;
  voice_title: string;
  seller_user_id: string;
  buyer_user_id: string;
  license_type: string;
  billing_unit: string;
  char_quota_total: number;
  char_quota_used: number;
  char_quota_remaining: number;
  price_paid_cents: number;
  payment_ref: string;
  status: string;
  expires_at?: string | null;
  created_at?: string | null;
}

export interface Complaint {
  complaint_id: string;
  catalog_id?: string | null;
  voice_version_id?: string | null;
  reporter_user_id: string;
  target_url: string;
  description: string;
  evidence_urls: string[];
  status: string;
  resolution_note?: string | null;
  created_at?: string | null;
  resolved_at?: string | null;
}

export async function purchaseCatalog(catalogId: string) {
  return apiJson<Authorization>(`/api/v1/catalog/voices/${catalogId}/purchase`, {
    method: "POST",
  });
}

export type CheckoutResult = {
  order_id: string;
  status: string;
  amount_cents: number;
  currency: string;
  provider: string;
  provider_ref: string;
  checkout_url?: string | null;
  authorization_id?: string | null;
};

export async function checkoutCatalog(catalogId: string) {
  return apiJson<CheckoutResult>(`/api/v1/catalog/voices/${catalogId}/checkout`, {
    method: "POST",
  });
}

export async function confirmMockPayment(orderId: string) {
  return apiJson<{ order_id: string; status: string; authorization_id: string }>(
    `/api/v1/payments/orders/${orderId}/mock-confirm`,
    { method: "POST" },
  );
}

export async function purchaseCatalogWithCheckout(catalogId: string, priceCents: number) {
  if (priceCents <= 0) {
    const auth = await purchaseCatalog(catalogId);
    return {
      order_id: auth.authorization_id,
      status: "paid",
      amount_cents: 0,
      currency: "CNY",
      provider: "mock",
      provider_ref: auth.payment_ref,
      authorization_id: auth.authorization_id,
    } satisfies CheckoutResult;
  }
  const checkout = await checkoutCatalog(catalogId);
  if (checkout.status === "pending") {
    const confirmed = await confirmMockPayment(checkout.order_id);
    return {
      ...checkout,
      status: confirmed.status,
      authorization_id: confirmed.authorization_id,
    };
  }
  return checkout;
}

export async function fetchMyAuthorizations() {
  return apiJson<Authorization[]>("/api/v1/authorizations");
}

export async function fetchAuthorizationCertificate(authorizationId: string) {
  return apiJson<Record<string, unknown>>(
    `/api/v1/authorizations/${authorizationId}/certificate`,
  );
}

export async function fetchAuthorizationVerify(authorizationId: string) {
  return apiJson<{
    authorization_id: string;
    status: string;
    valid: boolean;
    voice_title: string;
    license_type: string;
    message: string;
  }>(`/api/v1/authorizations/${authorizationId}/verify`);
}

export async function fetchIssuedAuthorizations() {
  return apiJson<Authorization[]>("/api/v1/authorizations/issued");
}

export async function submitComplaint(body: {
  catalog_id?: string;
  voice_version_id?: string;
  target_url?: string;
  description: string;
  evidence_urls?: string[];
}) {
  return apiJson<Complaint>("/api/v1/complaints", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function updateCatalogLicense(
  catalogId: string,
  body: {
    license_type: string;
    price_cents: number;
    billing_unit: string;
    included_chars: number;
    prohibited_domains: string[];
  },
) {
  return apiJson<CatalogEntry>(`/api/v1/catalog/voices/${catalogId}/license`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function formatPriceCents(cents: number): string {
  if (cents <= 0) return "免费";
  return `¥${(cents / 100).toFixed(2)}`;
}

export interface CreatorProfile {
  user_id: string;
  display_name: string;
  bio: string;
  published_count: number;
  voices: CatalogEntry[];
}

export interface VoiceGrant {
  grant_id: string;
  voice_id: string;
  voice_name: string;
  granter_user_id: string;
  grantee_user_id: string;
  scope: string;
  expires_at?: string | null;
  created_at?: string | null;
}

export interface VoiceSummary {
  voice_id: string;
  name: string;
  version_count: number;
  latest_version_id?: string | null;
}

export async function fetchCatalogTags() {
  return apiJson<string[]>("/api/v1/catalog/tags");
}

export async function fetchCatalog(opts?: { featured?: boolean; tags?: string[]; owner?: string }) {
  const params = new URLSearchParams();
  if (opts?.featured) params.set("featured", "true");
  if (opts?.tags?.length) params.set("tags", opts.tags.join(","));
  if (opts?.owner) params.set("owner", opts.owner);
  const q = params.toString();
  return apiJson<CatalogEntry[]>(`/api/v1/catalog/voices${q ? `?${q}` : ""}`);
}

export async function fetchCreatorProfile(
  ownerUserId: string,
  opts?: { featured?: boolean; tags?: string[] },
) {
  const params = new URLSearchParams();
  if (opts?.featured) params.set("featured", "true");
  if (opts?.tags?.length) params.set("tags", opts.tags.join(","));
  const q = params.toString();
  return apiJson<CreatorProfile>(
    `/api/v1/catalog/creators/${ownerUserId}${q ? `?${q}` : ""}`,
  );
}

export async function fetchMyCatalogSubmissions() {
  return apiJson<CatalogEntry[]>("/api/v1/catalog/voices/mine");
}

export async function fetchPendingCatalog() {
  return apiJson<CatalogEntry[]>("/api/v1/catalog/voices/pending");
}

export async function approveCatalogEntry(catalogId: string) {
  return apiJson<CatalogEntry>(`/api/v1/catalog/voices/${catalogId}/approve`, { method: "POST" });
}

export async function rejectCatalogEntry(catalogId: string) {
  return apiJson<CatalogEntry>(`/api/v1/catalog/voices/${catalogId}/reject`, { method: "POST" });
}

export async function publishToCatalog(body: {
  voice_version_id: string;
  title: string;
  description?: string;
  tags?: string[];
  featured?: boolean;
  demo_text?: string;
  license_type?: string;
  price_cents?: number;
  billing_unit?: string;
  included_chars?: number;
  prohibited_domains?: string[];
}) {
  return apiJson<CatalogEntry>("/api/v1/catalog/voices", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchMyVoices() {
  return apiJson<VoiceSummary[]>("/api/v1/voices");
}

export async function fetchReceivedGrants() {
  return apiJson<VoiceGrant[]>("/api/v1/voice-grants");
}

export async function fetchIssuedGrants() {
  return apiJson<VoiceGrant[]>("/api/v1/voice-grants/issued");
}

/** Tolerates older API builds that lack /voice-grants/issued (404). */
export async function fetchIssuedGrantsOptional(): Promise<VoiceGrant[]> {
  try {
    return await fetchIssuedGrants();
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      return [];
    }
    throw e;
  }
}

export async function regenerateCatalogDemo(catalogId: string) {
  return apiJson<CatalogEntry>(`/api/v1/catalog/voices/${catalogId}/generate-demo`, {
    method: "POST",
  });
}

export async function createVoiceGrant(voiceId: string, granteeUserId: string) {
  return apiJson<VoiceGrant>(`/api/v1/voices/${voiceId}/grants`, {
    method: "POST",
    body: JSON.stringify({ grantee_user_id: granteeUserId }),
  });
}

export async function revokeVoiceGrant(grantId: string) {
  return apiJson<void>(`/api/v1/voice-grants/${grantId}`, { method: "DELETE" });
}

/** Preset dev users for local cross-account demos (DEV_SKIP_AUTH). */
export const DEV_USER_PRESETS = [
  {
    id: "00000000-0000-0000-0000-000000000001",
    label: "用户 A（音色 owner）",
  },
  {
    id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    label: "用户 B（被授权方）",
  },
  {
    id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    label: "用户 C（运营审核）",
  },
] as const;

export const DEV_ADMIN_USER_ID = DEV_USER_PRESETS[2].id;

export function getDevUserId(): string {
  return localStorage.getItem("dev_user_id") ?? DEV_USER_PRESETS[0].id;
}

export function setDevUserId(userId: string) {
  localStorage.setItem("dev_user_id", userId);
}
