import { apiJson } from "./client";

export type SellerWallet = {
  seller_user_id: string;
  balance_cents: number;
  pending_payout_cents: number;
  total_earned_cents: number;
  platform_fee_bps: number;
  min_payout_cents: number;
};

export type SellerLedgerEntry = {
  entry_id: string;
  kind: string;
  gross_cents: number;
  fee_cents: number;
  net_cents: number;
  balance_after_cents: number;
  payment_order_id?: string | null;
  note?: string | null;
  created_at?: string | null;
};

export type PayoutRequest = {
  payout_id: string;
  seller_user_id: string;
  amount_cents: number;
  status: string;
  note?: string | null;
  created_at?: string | null;
  processed_at?: string | null;
};

export async function fetchSellerWallet() {
  return apiJson<SellerWallet>("/api/v1/seller/wallet");
}

export async function fetchSellerLedger() {
  return apiJson<SellerLedgerEntry[]>("/api/v1/seller/ledger");
}

export async function requestSellerPayout(amountCents: number) {
  return apiJson<PayoutRequest>("/api/v1/seller/payouts", {
    method: "POST",
    body: JSON.stringify({ amount_cents: amountCents }),
  });
}

export async function fetchAdminPayouts(status = "pending") {
  return apiJson<PayoutRequest[]>(`/api/v1/admin/payouts?status=${status}`);
}

export async function approveAdminPayout(payoutId: string, note?: string) {
  return apiJson<PayoutRequest>(`/api/v1/admin/payouts/${payoutId}/approve`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export async function rejectAdminPayout(payoutId: string, note?: string) {
  return apiJson<PayoutRequest>(`/api/v1/admin/payouts/${payoutId}/reject`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}
