import { apiJson } from "@/api/client";

export interface ApiKeySummary {
  key_id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  revoked: boolean;
  webhook_url?: string | null;
  last_used_at?: string | null;
  created_at?: string | null;
}

export interface ApiKeyCreated {
  key_id: string;
  name: string;
  key_prefix: string;
  api_key: string;
  scopes: string[];
  created_at?: string | null;
}

export function fetchDeveloperApiKeys(): Promise<ApiKeySummary[]> {
  return apiJson<ApiKeySummary[]>("/api/v1/developer/api-keys");
}

export function createDeveloperApiKey(name: string): Promise<ApiKeyCreated> {
  return apiJson<ApiKeyCreated>("/api/v1/developer/api-keys", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function revokeDeveloperApiKey(keyId: string): Promise<ApiKeySummary> {
  return apiJson<ApiKeySummary>(`/api/v1/developer/api-keys/${keyId}`, {
    method: "DELETE",
  });
}

export function updateDeveloperApiKeyWebhook(
  keyId: string,
  body: { webhook_url?: string | null; webhook_secret?: string | null },
): Promise<ApiKeySummary> {
  return apiJson<ApiKeySummary>(`/api/v1/developer/api-keys/${keyId}/webhook`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export interface WebhookDeliverySummary {
  delivery_id: string;
  channel: string;
  target_url: string;
  status: string;
  attempts: number;
  max_attempts: number;
  last_status_code?: number | null;
  last_error?: string | null;
  delivered_at?: string | null;
  created_at?: string | null;
}

export function fetchAdminWebhookDeliveries(limit = 50): Promise<WebhookDeliverySummary[]> {
  return apiJson<WebhookDeliverySummary[]>(`/api/v1/admin/webhook-deliveries?limit=${limit}`);
}
