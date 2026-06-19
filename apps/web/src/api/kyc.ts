import { apiJson } from "./client";

export type KycStatus = {
  verified: boolean;
  verified_at: string | null;
  required: boolean;
  provider: string | null;
};

export async function fetchKycStatus() {
  return apiJson<KycStatus>("/api/v1/kyc/status");
}

export type AdminKycUser = {
  user_id: string;
  phone: string;
  verified: boolean;
  verified_at: string | null;
  created_at: string;
};

export type KycAuditEntry = {
  audit_id: string;
  user_id: string;
  action: string;
  status: string;
  provider: string;
  message: string | null;
  real_name_masked: string | null;
  id_number_last4: string | null;
  created_at: string;
};

export async function fetchAdminKycPending() {
  return apiJson<AdminKycUser[]>("/api/v1/admin/kyc/pending");
}

export async function fetchAdminKycAudit(userId: string) {
  return apiJson<KycAuditEntry[]>(`/api/v1/admin/kyc/${userId}/audit`);
}

export async function submitKyc(realName: string, idNumber: string) {
  return apiJson<{ verified: boolean; message: string; audit_id: string }>("/api/v1/kyc/submit", {
    method: "POST",
    body: JSON.stringify({ real_name: realName, id_number: idNumber }),
  });
}

export async function adminVerifyKyc(userId: string, note?: string) {
  return apiJson<KycStatus>(`/api/v1/admin/kyc/${userId}/verify`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export async function adminRevokeKyc(userId: string, note?: string) {
  return apiJson<KycStatus>(`/api/v1/admin/kyc/${userId}/revoke`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}
