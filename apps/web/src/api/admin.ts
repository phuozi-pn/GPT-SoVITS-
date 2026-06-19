import { apiJson, type JobResponse } from "./client";
import type { Complaint } from "./catalog";

export type AdminComplaint = Complaint;

export interface AdminJobListResponse {
  items: JobResponse[];
  total: number;
}

export interface PlatformStatsResponse {
  release: string;
  jobs_queued: number;
  jobs_running: number;
  jobs_failed_24h: number;
}

export async function fetchAdminJobs(opts?: {
  status?: string;
  job_type?: string;
  owner?: string;
  limit?: number;
}) {
  const params = new URLSearchParams();
  if (opts?.status) params.set("status", opts.status);
  if (opts?.job_type) params.set("job_type", opts.job_type);
  if (opts?.owner) params.set("owner", opts.owner);
  if (opts?.limit) params.set("limit", String(opts.limit));
  const q = params.toString();
  return apiJson<AdminJobListResponse>(`/api/v1/admin/jobs${q ? `?${q}` : ""}`);
}

export async function fetchPlatformStats() {
  return apiJson<PlatformStatsResponse>("/api/v1/admin/stats");
}

export async function fetchAdminComplaints() {
  return apiJson<AdminComplaint[]>("/api/v1/admin/complaints");
}

export async function resolveComplaintTakedown(complaintId: string, resolutionNote = "") {
  const params = new URLSearchParams();
  if (resolutionNote) params.set("resolution_note", resolutionNote);
  const q = params.toString();
  return apiJson<AdminComplaint>(
    `/api/v1/admin/complaints/${complaintId}/takedown${q ? `?${q}` : ""}`,
    { method: "POST" },
  );
}

export async function dismissComplaint(complaintId: string, resolutionNote = "") {
  const params = new URLSearchParams();
  if (resolutionNote) params.set("resolution_note", resolutionNote);
  const q = params.toString();
  return apiJson<AdminComplaint>(
    `/api/v1/admin/complaints/${complaintId}/dismiss${q ? `?${q}` : ""}`,
    { method: "POST" },
  );
}

export type PaymentOrder = {
  order_id: string;
  authorization_id: string;
  catalog_id: string;
  buyer_user_id: string;
  seller_user_id: string;
  amount_cents: number;
  currency: string;
  status: string;
  provider: string;
  provider_ref: string;
  created_at: string | null;
};

export async function fetchAdminPayments(limit = 50) {
  return apiJson<PaymentOrder[]>(`/api/v1/admin/payments?limit=${limit}`);
}
