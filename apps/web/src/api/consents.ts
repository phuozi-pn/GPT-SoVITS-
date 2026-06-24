import { apiJson } from "@/api/client";

export interface ConsentAdminSummary {
  consent_id: string;
  voice_id: string;
  owner_user_id: string;
  voice_name: string;
  status: string;
  created_at?: string | null;
  approved_at?: string | null;
  reject_reason?: string | null;
}

export function fetchAdminPendingConsents(): Promise<ConsentAdminSummary[]> {
  return apiJson<ConsentAdminSummary[]>("/api/v1/admin/consents/pending");
}

export function approveAdminConsent(consentId: string): Promise<ConsentAdminSummary> {
  return apiJson<ConsentAdminSummary>(`/api/v1/admin/consents/${consentId}/approve`, {
    method: "POST",
  });
}

export function rejectAdminConsent(consentId: string, reason: string): Promise<ConsentAdminSummary> {
  return apiJson<ConsentAdminSummary>(`/api/v1/admin/consents/${consentId}/reject`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}
