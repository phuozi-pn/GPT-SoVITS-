<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  dismissComplaint,
  fetchAdminComplaints,
  fetchAdminJobs,
  fetchAdminPayments,
  fetchPlatformStats,
  resolveComplaintTakedown,
  type AdminComplaint,
  type PaymentOrder,
} from "@/api/admin";
import {
  adminRevokeKyc,
  adminVerifyKyc,
  fetchAdminKycAudit,
  fetchAdminKycPending,
  type AdminKycUser,
  type KycAuditEntry,
} from "@/api/kyc";
import type { JobResponse } from "@/api/client";
import {
  approveAdminPayout,
  fetchAdminPayouts,
  rejectAdminPayout,
  type PayoutRequest,
} from "@/api/settlement";
import { DEV_ADMIN_USER_ID, getDevUserId } from "@/api/catalog";
import PageHero from "@/components/PageHero.vue";
import PageSurface from "@/components/PageSurface.vue";
import RackPanel from "@/modules/voice/components/studio/RackPanel.vue";
import AppModal from "@/components/AppModal.vue";
import PageActionBar from "@/components/PageActionBar.vue";
import PageActionLink from "@/components/PageActionLink.vue";
import { formatApiError } from "@/utils/apiErrors";
import { isLabsEnabled } from "@/config/features";

const router = useRouter();
const stats = ref({
  release: "—",
  jobs_queued: 0,
  jobs_running: 0,
  jobs_failed_24h: 0,
});
const jobs = ref<JobResponse[]>([]);
const complaints = ref<AdminComplaint[]>([]);
const kycPending = ref<AdminKycUser[]>([]);
const payments = ref<PaymentOrder[]>([]);
const payouts = ref<PayoutRequest[]>([]);
const kycAuditUserId = ref("");
const kycAudit = ref<KycAuditEntry[]>([]);
const statusFilter = ref("");
const typeFilter = ref("");
const ownerFilter = ref("");
const loading = ref(false);
const error = ref("");
const toast = ref("");

type AdminModal = "" | "complaints" | "kyc" | "payouts" | "payments";
const activeModal = ref<AdminModal>("");

function openModal(id: AdminModal) {
  activeModal.value = id;
}

function closeModal() {
  activeModal.value = "";
}

const isAdmin = computed(() => getDevUserId() === DEV_ADMIN_USER_ID);

function shortId(id: string): string {
  return id.slice(0, 8);
}

function statusClass(status: string): string {
  if (status === "failed") return "pill pill--danger";
  if (status === "succeeded") return "pill pill--ok";
  if (status === "running") return "pill pill--warn";
  return "pill";
}

async function copyTrace(traceId: string | null | undefined) {
  if (!traceId) return;
  try {
    await navigator.clipboard.writeText(traceId);
    toast.value = "已复制 trace_id";
    setTimeout(() => {
      toast.value = "";
    }, 2000);
  } catch {
    toast.value = "复制失败";
  }
}

async function reload() {
  if (!isAdmin.value) return;
  loading.value = true;
  error.value = "";
  try {
    const [s, j, c, k, p, po] = await Promise.all([
      fetchPlatformStats(),
      fetchAdminJobs({
        status: statusFilter.value || undefined,
        job_type: typeFilter.value || undefined,
        owner: ownerFilter.value.trim() || undefined,
        limit: 80,
      }),
      fetchAdminComplaints(),
      fetchAdminKycPending(),
      fetchAdminPayments(40),
      fetchAdminPayouts("pending"),
    ]);
    stats.value = s;
    jobs.value = j.items;
    complaints.value = c;
    kycPending.value = k;
    payments.value = p;
    payouts.value = po;
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
}

async function onTakedown(complaintId: string) {
  try {
    await resolveComplaintTakedown(complaintId, "运营下架处理");
    await reload();
    toast.value = "已下架并撤销授权";
  } catch (e) {
    error.value = formatApiError(e);
  }
}

async function onDismiss(complaintId: string) {
  try {
    await dismissComplaint(complaintId, "不构成侵权");
    await reload();
    toast.value = "已驳回投诉";
  } catch (e) {
    error.value = formatApiError(e);
  }
}

async function onKycVerify(userId: string) {
  try {
    await adminVerifyKyc(userId, "运营人工通过");
    await reload();
    toast.value = "已通过实名";
  } catch (e) {
    error.value = formatApiError(e);
  }
}

async function onKycRevoke(userId: string) {
  try {
    await adminRevokeKyc(userId, "运营撤销");
    await reload();
    toast.value = "已撤销实名";
  } catch (e) {
    error.value = formatApiError(e);
  }
}

async function loadKycAudit(userId: string) {
  kycAuditUserId.value = userId;
  try {
    kycAudit.value = await fetchAdminKycAudit(userId);
  } catch (e) {
    error.value = formatApiError(e);
  }
}

async function onApprovePayout(payoutId: string) {
  try {
    await approveAdminPayout(payoutId, "运营 mock 打款");
    await reload();
    toast.value = "提现已批准";
  } catch (e) {
    error.value = formatApiError(e);
  }
}

async function onRejectPayout(payoutId: string) {
  try {
    await rejectAdminPayout(payoutId, "信息不符");
    await reload();
    toast.value = "提现已驳回";
  } catch (e) {
    error.value = formatApiError(e);
  }
}

onMounted(() => {
  if (!isAdmin.value) {
    router.replace("/library");
    return;
  }
  void reload();
});
</script>

<template>
  <div class="page page--full admin-page">
    <div v-if="error" class="alert alert--error">{{ error }}</div>
    <div v-if="toast" class="alert alert--ok">{{ toast }}</div>

    <PageSurface>
      <PageHero compact flow hint="筛选任务后可复制 trace_id；各运营队列从底部链接打开。">
      <template #stats>
        <p class="page-metrics">
          Release <strong>{{ stats.release }}</strong>
          · 排队 <strong>{{ stats.jobs_queued }}</strong>
          · 运行中 <strong>{{ stats.jobs_running }}</strong>
          · 24h 失败
          <strong :class="{ 'page-metrics__danger': stats.jobs_failed_24h > 0 }">{{ stats.jobs_failed_24h }}</strong>
          · 投诉
          <strong :class="{ 'page-metrics__danger': complaints.length > 0 }">{{ complaints.length }}</strong>
          · 待实名
          <strong :class="{ 'page-metrics__danger': kycPending.length > 0 }">{{ kycPending.length }}</strong>
          · 待提现
          <strong :class="{ 'page-metrics__danger': payouts.length > 0 }">{{ payouts.length }}</strong>
        </p>
      </template>
      <template #actions>
        <button class="btn btn--primary btn--sm" :disabled="loading" @click="reload">刷新</button>
      </template>
      </PageHero>

      <RackPanel label="运维" title="任务列表">
      <div class="admin-filters">
        <label>
          状态
          <select v-model="statusFilter" @change="reload">
            <option value="">全部</option>
            <option value="queued">queued</option>
            <option value="running">running</option>
            <option value="succeeded">succeeded</option>
            <option value="failed">failed</option>
          </select>
        </label>
        <label>
          类型
          <select v-model="typeFilter" @change="reload">
            <option value="">全部</option>
            <option value="synthesize">synthesize</option>
            <option value="train">train</option>
            <option value="batch">batch</option>
          </select>
        </label>
        <label>
          Owner UUID
          <input v-model="ownerFilter" placeholder="筛选 owner_user_id" @keyup.enter="reload" />
        </label>
      </div>

      <div class="admin-table-wrap">
        <table v-if="jobs.length" class="admin-table">
          <thead>
            <tr>
              <th>Job</th>
              <th>Owner</th>
              <th>类型</th>
              <th>状态</th>
              <th>Trace</th>
              <th>错误</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="j in jobs" :key="j.job_id">
              <td class="mono">{{ shortId(j.job_id) }}</td>
              <td class="mono">{{ j.owner_user_id ? shortId(j.owner_user_id) : "—" }}</td>
              <td>{{ j.job_type }}</td>
              <td><span :class="statusClass(j.status)">{{ j.status }}</span></td>
              <td class="mono">
                <button
                  v-if="j.trace_id"
                  type="button"
                  class="text-action mono"
                  :title="j.trace_id"
                  @click="copyTrace(j.trace_id)"
                >
                  {{ shortId(j.trace_id) }}
                </button>
                <span v-else>—</span>
              </td>
              <td class="admin-table__err">{{ j.error_message || "—" }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="hint">{{ loading ? "加载中…" : "暂无任务记录" }}</p>
      </div>
      </RackPanel>

      <PageActionBar label="运营队列">
        <PageActionLink :badge="complaints.length" @click="openModal('complaints')">侵权投诉</PageActionLink>
        <PageActionLink :badge="kycPending.length" @click="openModal('kyc')">实名审核</PageActionLink>
        <PageActionLink :badge="payouts.length" @click="openModal('payouts')">卖家提现</PageActionLink>
        <PageActionLink v-if="isLabsEnabled()" @click="openModal('payments')">支付订单</PageActionLink>
      </PageActionBar>
    </PageSurface>

    <AppModal :open="activeModal === 'complaints'" label="合规" title="侵权投诉队列" wide @close="closeModal">
      <ul v-if="complaints.length" class="grant-list">
        <li v-for="c in complaints" :key="c.complaint_id">
          <span>
            {{ shortId(c.complaint_id) }} ·
            {{ c.description.slice(0, 80) }}{{ c.description.length > 80 ? "…" : "" }}
          </span>
          <span class="row-actions">
            <button class="btn btn--primary btn--sm" @click="onTakedown(c.complaint_id)">下架</button>
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <button class="text-action text-action--danger" @click="onDismiss(c.complaint_id)">驳回</button>
          </span>
        </li>
      </ul>
      <p v-else class="hint">暂无待处理投诉</p>
    </AppModal>

    <AppModal :open="activeModal === 'kyc'" label="KYC" title="待实名用户" wide @close="closeModal">
      <ul v-if="kycPending.length" class="grant-list">
        <li v-for="u in kycPending" :key="u.user_id">
          <span class="mono">{{ shortId(u.user_id) }} · {{ u.phone }}</span>
          <span class="row-actions">
            <button class="text-action" @click="loadKycAudit(u.user_id)">审计</button>
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <button class="btn btn--primary btn--sm" @click="onKycVerify(u.user_id)">通过</button>
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <button class="text-action text-action--danger" @click="onKycRevoke(u.user_id)">撤销</button>
          </span>
        </li>
      </ul>
      <p v-else class="hint">暂无待审核用户</p>
      <ul v-if="kycAudit.length && kycAuditUserId" class="grant-list admin-audit">
        <li v-for="a in kycAudit" :key="a.audit_id">
          {{ a.action }} / {{ a.status }} · {{ a.message || "—" }}
        </li>
      </ul>
    </AppModal>

    <AppModal :open="activeModal === 'payouts'" label="结算" title="卖家提现队列" @close="closeModal">
      <ul v-if="payouts.length" class="grant-list">
        <li v-for="p in payouts" :key="p.payout_id">
          <span>
            {{ shortId(p.seller_user_id) }} · ¥{{ (p.amount_cents / 100).toFixed(2) }} · {{ p.status }}
          </span>
          <span class="row-actions">
            <button class="btn btn--primary btn--sm" @click="onApprovePayout(p.payout_id)">打款</button>
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <button class="text-action text-action--danger" @click="onRejectPayout(p.payout_id)">驳回</button>
          </span>
        </li>
      </ul>
      <p v-else class="hint">暂无待处理提现</p>
    </AppModal>

    <AppModal :open="activeModal === 'payments'" label="支付" title="近期支付订单" wide @close="closeModal">
      <div class="admin-table-wrap">
        <table v-if="payments.length" class="admin-table">
          <thead>
            <tr>
              <th>订单</th>
              <th>金额</th>
              <th>买家</th>
              <th>卖家</th>
              <th>Ref</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in payments" :key="p.order_id">
              <td class="mono">{{ shortId(p.order_id) }}</td>
              <td>¥{{ (p.amount_cents / 100).toFixed(2) }}</td>
              <td class="mono">{{ shortId(p.buyer_user_id) }}</td>
              <td class="mono">{{ shortId(p.seller_user_id) }}</td>
              <td class="mono">{{ p.provider_ref }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="hint">暂无支付记录</p>
      </div>
    </AppModal>
  </div>
</template>

<style scoped>
.admin-filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.admin-table-wrap {
  overflow-x: auto;
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.admin-table th,
.admin-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--color-brushed);
  text-align: left;
  vertical-align: top;
}

.admin-table th {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-brushed-dark);
}

.admin-table .mono {
  font-family: var(--font-mono);
  font-size: 12px;
}

.admin-table__err {
  max-width: 280px;
  word-break: break-word;
  color: var(--color-peak-red);
}

.pill--danger {
  background: rgb(199 93 77 / 0.15);
  color: var(--color-peak-red);
}

.pill--ok {
  background: rgb(80 140 90 / 0.15);
  color: #3d6b45;
}

.pill--warn {
  background: rgb(232 160 80 / 0.2);
  color: #9a5a18;
}

.admin-audit {
  margin-top: 12px;
  font-size: 12px;
  color: var(--color-brushed-dark);
}
</style>
