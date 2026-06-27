<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { fetchQuota } from "@/api/client";
import {
  fetchTokenPackages,
  fetchWallet,
  fetchWalletLedger,
  purchaseTokenPackage,
  type TokenPackage,
  type WalletLedgerEntry,
} from "@/api/wallet";
import ErrorBanner from "@/components/ErrorBanner.vue";
import PageActionBar from "@/components/PageActionBar.vue";
import PageHero from "@/components/PageHero.vue";
import PageSurface from "@/components/PageSurface.vue";
import QuotaUsageMeters from "@/components/QuotaUsageMeters.vue";
import { getPageMeta } from "@/config/navigation";
import { useToast } from "@/composables/useToast";
import type { QuotaSummary } from "@/types/api";
import { formatApiError } from "@/utils/apiErrors";
import {
  formatPriceYuan,
  formatTokenVolumeWithUnit,
  ledgerKindLabel,
} from "@/utils/quotaDisplay";

const pageMeta = getPageMeta("/account", "account");
const { toastOk } = useToast();

const loading = ref(false);
const purchasing = ref<string | null>(null);
const error = ref("");
const walletBalance = ref(0);
const totalPurchased = ref(0);
const quota = ref<QuotaSummary | null>(null);
const packages = ref<TokenPackage[]>([]);
const ledger = ref<WalletLedgerEntry[]>([]);

const totalAvailable = computed(() =>
  quota.value?.total_tokens_remaining ??
  (quota.value?.chars_remaining ?? 0) + walletBalance.value,
);

function formatTime(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

async function reload() {
  loading.value = true;
  error.value = "";
  try {
    const [w, q, pkgs, entries] = await Promise.all([
      fetchWallet(),
      fetchQuota(),
      fetchTokenPackages(),
      fetchWalletLedger(30),
    ]);
    walletBalance.value = w.token_balance;
    totalPurchased.value = w.total_purchased_tokens;
    quota.value = q;
    packages.value = pkgs;
    ledger.value = entries;
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
}

async function onPurchase(pkg: TokenPackage) {
  if (purchasing.value) return;
  purchasing.value = pkg.sku;
  error.value = "";
  try {
    const res = await purchaseTokenPackage(pkg.sku);
    walletBalance.value = res.token_balance;
    toastOk(`已充值 ${formatTokenVolumeWithUnit(res.tokens_granted)}（Mock 支付）`);
    await reload();
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    purchasing.value = null;
  }
}

onMounted(reload);
</script>

<template>
  <div class="page page--full account-page">
    <ErrorBanner v-if="error" :message="error" retry :loading="loading" @retry="reload" @dismiss="error = ''" />

    <PageSurface>
      <PageHero compact flow :title="pageMeta.label" :hint="pageMeta.desc">
        <template #stats>
          <p class="page-metrics">
            钱包余额 <strong>{{ formatTokenVolumeWithUnit(walletBalance) }}</strong>
            · 可用合计 <strong>{{ formatTokenVolumeWithUnit(totalAvailable) }}</strong>
          </p>
        </template>
        <template #actions>
          <button type="button" class="text-action" :disabled="loading" @click="reload">刷新</button>
        </template>
      </PageHero>

      <section class="account-balance card-surface">
        <div class="account-balance__main">
          <p class="account-balance__label">Token 钱包余额</p>
          <p class="account-balance__value">{{ formatTokenVolumeWithUnit(walletBalance) }}</p>
          <p class="hint">累计购买 {{ formatTokenVolumeWithUnit(totalPurchased) }} · Mock 支付即时到账</p>
        </div>
        <div v-if="quota" class="account-balance__quota">
          <QuotaUsageMeters :quota="quota" layout="inline" />
        </div>
      </section>

      <section class="account-packages">
        <div class="section-head">
          <div>
            <h2 class="section-head__title">购买 Token 包</h2>
            <p class="section-head__hint">平台内 Mock 支付，无需真实扣款；优先消耗本月免费额度，超出部分扣钱包</p>
          </div>
        </div>
        <div class="package-grid">
          <article v-for="pkg in packages" :key="pkg.sku" class="package-card card-surface">
            <h3 class="package-card__title">{{ pkg.label }}</h3>
            <p class="package-card__amount">{{ formatTokenVolumeWithUnit(pkg.token_amount) }}</p>
            <p class="package-card__price">{{ formatPriceYuan(pkg.price_cents) }}</p>
            <p class="hint package-card__hint">{{ pkg.hint }}</p>
            <button
              type="button"
              class="btn btn--primary btn--sm package-card__btn"
              :disabled="!!purchasing || loading"
              @click="onPurchase(pkg)"
            >
              {{ purchasing === pkg.sku ? "充值中…" : "Mock 购买" }}
            </button>
          </article>
        </div>
      </section>

      <section v-if="ledger.length" class="account-ledger">
        <div class="section-head">
          <div>
            <h2 class="section-head__title">钱包流水</h2>
            <p class="section-head__hint">充值与合成超额扣减记录</p>
          </div>
        </div>
        <div class="ledger-table-wrap">
          <table class="ledger-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>类型</th>
                <th>变动</th>
                <th>余额</th>
                <th>备注</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in ledger" :key="row.entry_id">
                <td>{{ formatTime(row.created_at) }}</td>
                <td>{{ ledgerKindLabel(row.kind) }}</td>
                <td :class="row.token_delta >= 0 ? 'ledger-pos' : 'ledger-neg'">
                  {{ row.token_delta >= 0 ? "+" : "" }}{{ formatTokenVolumeWithUnit(row.token_delta) }}
                </td>
                <td>{{ formatTokenVolumeWithUnit(row.balance_after) }}</td>
                <td class="ledger-note">{{ row.note ?? "—" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <PageActionBar label="相关">
        <router-link to="/history" class="page-action-link">合成历史</router-link>
        <router-link to="/library" class="page-action-link">智能配音</router-link>
        <router-link to="/projects" class="page-action-link">短剧批量</router-link>
      </PageActionBar>
    </PageSurface>
  </div>
</template>

<style scoped>
.account-page {
  gap: 12px;
}

.card-surface {
  padding: 16px;
  border: 1px solid var(--color-brushed);
  border-radius: var(--radius-module);
  background: var(--bg-surface-glass);
}

.account-balance {
  display: grid;
  gap: 16px;
}

@media (min-width: 768px) {
  .account-balance {
    grid-template-columns: minmax(200px, 280px) 1fr;
    align-items: start;
  }
}

.account-balance__label {
  margin: 0;
  font-size: 12px;
  color: var(--color-ink-muted);
}

.account-balance__value {
  margin: 4px 0 8px;
  font-size: 28px;
  font-weight: 700;
  color: var(--color-vu-amber);
}

.package-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

.package-card {
  display: grid;
  gap: 6px;
}

.package-card__title {
  margin: 0;
  font-size: 16px;
}

.package-card__amount {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.package-card__price {
  margin: 0;
  font-family: var(--font-mono);
  color: var(--color-ink-muted);
}

.package-card__btn {
  margin-top: 8px;
  justify-self: start;
}

.ledger-table-wrap {
  overflow-x: auto;
}

.ledger-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.ledger-table th,
.ledger-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
  text-align: left;
}

.ledger-table th {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.ledger-pos {
  color: var(--color-vu-amber);
}

.ledger-neg {
  color: var(--color-ink-muted);
}

.ledger-note {
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-ink-muted);
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
  margin-bottom: 12px;
}

.section-head__title {
  margin: 0;
  font-size: 18px;
}

.section-head__hint {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-ink-muted);
}

.account-packages,
.account-ledger {
  margin-top: 20px;
}
</style>
