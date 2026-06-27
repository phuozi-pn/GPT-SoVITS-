import { apiJson } from "@/api/client";

export type UserWallet = {
  user_id: string;
  token_balance: number;
  total_purchased_tokens: number;
};

export type TokenPackage = {
  sku: string;
  label: string;
  token_amount: number;
  price_cents: number;
  hint: string;
  mock_payment: boolean;
};

export type WalletLedgerEntry = {
  entry_id: string;
  kind: string;
  token_delta: number;
  balance_after: number;
  job_id?: string | null;
  package_sku?: string | null;
  note?: string | null;
  created_at: string;
};

export type WalletPurchaseResult = {
  package_sku: string;
  tokens_granted: number;
  token_balance: number;
  mock_payment: boolean;
};

export function fetchWallet() {
  return apiJson<UserWallet>("/api/v1/wallet");
}

export function fetchTokenPackages() {
  return apiJson<TokenPackage[]>("/api/v1/wallet/packages");
}

export function fetchWalletLedger(limit = 50) {
  return apiJson<WalletLedgerEntry[]>(`/api/v1/wallet/ledger?limit=${limit}`);
}

export function purchaseTokenPackage(packageSku: string) {
  return apiJson<WalletPurchaseResult>("/api/v1/wallet/purchase", {
    method: "POST",
    body: JSON.stringify({ package_sku: packageSku }),
  });
}
