<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { QUOTA_TIERS } from "@/constants/quotaTiers";
import { useRouter } from "vue-router";
import {
  dismissComplaint,
  fetchAdminComplaints,
  fetchAdminJobs,
  fetchAdminPayments,
  fetchAdminUsageReport,
  updateAdminUserQuota,
  type UserUsageReportRow,
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
import {
  approveAdminConsent,
  fetchAdminPendingConsents,
  rejectAdminConsent,
  type ConsentAdminSummary,
} from "@/api/consents";
import {
  createAdminInviteCode,
  fetchAdminInviteCodes,
  fetchAdminWaitlist,
  issueWaitlistInvite,
  type InviteCodeSummary,
  type WaitlistEntrySummary,
} from "@/api/marketplace";
import {
  fetchAdminWebhookDeliveries,
  type WebhookDeliverySummary,
} from "@/api/developer";
import { DEV_ADMIN_USER_ID, getDevUserId } from "@/api/catalog";
import PageHero from "@/components/PageHero.vue";
import QuotaUsageMeters from "@/components/QuotaUsageMeters.vue";
import { formatTokenVolumeWithUnit } from "@/utils/quotaDisplay";
import PageSurface from "@/components/PageSurface.vue";
import RackPanel from "@/modules/voice/components/studio/RackPanel.vue";
import AppModal from "@/components/AppModal.vue";
import PageActionBar from "@/components/PageActionBar.vue";
import PageActionLink from "@/components/PageActionLink.vue";
import { formatApiError } from "@/utils/apiErrors";
import { isLabsEnabled } from "@/config/features";
import { ApiError } from "@/api/client";

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
const pendingConsents = ref<ConsentAdminSummary[]>([]);
const inviteCodes = ref<InviteCodeSummary[]>([]);
const waitlistEntries = ref<WaitlistEntrySummary[]>([]);
const webhookDeliveries = ref<WebhookDeliverySummary[]>([]);
const usageReport = ref<UserUsageReportRow[]>([]);
const usageMonth = ref("");
const quotaEditUser = ref<UserUsageReportRow | null>(null);
const quotaCharLimit = ref("");
const quotaTrainLimit = ref("");
const quotaSaving = ref(false);
const inviteCode = ref("");
const inviteMaxUses = ref(5);
const inviteNote = ref("");
const inviteExpiresDays = ref("");
const consentRejectReason = ref("");
const consentRejectId = ref("");
const kycAuditUserId = ref("");
const kycAudit = ref<KycAuditEntry[]>([]);
const statusFilter = ref("");
const typeFilter = ref("");
const ownerFilter = ref("");
const loading = ref(false);
const error = ref("");
const toast = ref("");

type AdminModal = "" | "complaints" | "kyc" | "payouts" | "payments" | "consents" | "consentReject" | "invites" | "webhooks" | "quota";
const activeModal = ref<AdminModal>("");

function openModal(id: AdminModal) {
  activeModal.value = id;
}

function closeModal() {
  activeModal.value = "";
  quotaEditUser.value = null;
}

function openQuotaEdit(row: UserUsageReportRow) {
  quotaEditUser.value = row;
  quotaCharLimit.value = String(row.monthly_char_limit);
  quotaTrainLimit.value = String(row.monthly_train_limit);
  activeModal.value = "quota";
}

function applyQuotaTier(tier: (typeof QUOTA_TIERS)[number]) {
  quotaCharLimit.value = String(tier.monthly_char_limit);
  quotaTrainLimit.value = String(tier.monthly_train_limit);
}

async function saveQuotaEdit() {
  if (!quotaEditUser.value) return;
  quotaSaving.value = true;
  error.value = "";
  try {
    await updateAdminUserQuota(quotaEditUser.value.user_id, {
      monthly_char_limit: Number(quotaCharLimit.value),
      monthly_train_limit: Number(quotaTrainLimit.value),
    });
    toast.value = "配额已更新";
    closeModal();
    await reload();
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    quotaSaving.value = false;
  }
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

function webhookStatusClass(status: string): string {
  if (status === "delivered") return "pill pill--ok";
  if (status === "failed") return "pill pill--danger";
  if (status === "retrying") return "pill pill--warn";
  return "pill";
}

async function fetchOptional<T>(fn: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await fn();
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      return fallback;
    }
    throw e;
  }
}

async function openWebhooksModal() {
  activeModal.value = "webhooks";
  try {
    webhookDeliveries.value = await fetchAdminWebhookDeliveries(40);
  } catch (e) {
    webhookDeliveries.value = [];
    if (e instanceof ApiError && e.status === 404) {
      error.value = "Webhook 审计接口未就绪，请重启 API（需迁移 025）";
    } else {
      error.value = formatApiError(e);
    }
  }
}

async function reload() {
  if (!isAdmin.value) return;
  loading.value = true;
  error.value = "";
  try {
    const [s, j, c, k, p, po, consents, invites, waitlist, usage] = await Promise.all([
      fetchPlatformStats(),
      fetchAdminJobs({
        status: statusFilter.value || undefined,
        job_type: typeFilter.value || undefined,
        owner: ownerFilter.value.trim() || undefined,
        limit: 80,
      }),
      fetchAdminComplaints(),
      fetchAdminKycPending(),
      isLabsEnabled() ? fetchAdminPayments(40) : Promise.resolve([]),
      fetchAdminPayouts("pending"),
      fetchAdminPendingConsents(),
      fetchOptional(() => fetchAdminInviteCodes(), []),
      fetchOptional(() => fetchAdminWaitlist(), []),
      fetchOptional(() => fetchAdminUsageReport(100), { billing_month: "", items: [], total: 0 }),
    ]);
    stats.value = s;
    jobs.value = j.items;
    complaints.value = c;
    kycPending.value = k;
    payments.value = p;
    payouts.value = po;
    pendingConsents.value = consents;
    inviteCodes.value = invites;
    waitlistEntries.value = waitlist;
    usageReport.value = usage.items;
    usageMonth.value = usage.billing_month;
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

async function onApproveConsent(consentId: string) {
  try {
    await approveAdminConsent(consentId);
    await reload();
    toast.value = "授权书已通过";
  } catch (e) {
    error.value = formatApiError(e);
  }
}

function openConsentReject(consentId: string) {
  consentRejectId.value = consentId;
  consentRejectReason.value = "授权材料不完整或无效";
  activeModal.value = "consentReject";
}

async function onRejectConsent() {
  if (!consentRejectId.value || !consentRejectReason.value.trim()) return;
  try {
    await rejectAdminConsent(consentRejectId.value, consentRejectReason.value.trim());
    consentRejectId.value = "";
    closeModal();
    await reload();
    toast.value = "授权书已驳回";
  } catch (e) {
    error.value = formatApiError(e);
  }
}

async function onCreateInvite() {
  const code = inviteCode.value.trim().toUpperCase();
  if (!code) return;
  try {
    const expiresRaw = inviteExpiresDays.value.trim();
    await createAdminInviteCode({
      code,
      max_uses: inviteMaxUses.value,
      note: inviteNote.value.trim(),
      expires_in_days: expiresRaw ? Number(expiresRaw) : null,
    });
    inviteCode.value = "";
    inviteNote.value = "";
    await reload();
    toast.value = `邀请码 ${code} 已创建`;
  } catch (e) {
    error.value = formatApiError(e);
  }
}

async function onIssueWaitlist(waitlistId: string) {
  try {
    const res = await issueWaitlistInvite(waitlistId);
    await reload();
    toast.value = res.code ? `已发码 ${res.code}` : res.message;
    setTimeout(() => {
      toast.value = "";
    }, 3000);
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
          · 待授权书
          <strong :class="{ 'page-metrics__danger': pendingConsents.length > 0 }">{{ pendingConsents.length }}</strong>
          · 待提现
          <strong :class="{ 'page-metrics__danger': payouts.length > 0 }">{{ payouts.length }}</strong>
        </p>
      </template>
      <template #actions>
        <button class="btn btn--primary btn--sm" :disabled="loading" @click="reload">刷新</button>
      </template>
      </PageHero>

      <RackPanel label="用量" :title="`用户使用量报表${usageMonth ? ` · ${usageMonth}` : ''}`">
        <div class="admin-table-wrap">
          <table v-if="usageReport.length" class="admin-table">
            <thead>
              <tr>
                <th>用户</th>
                <th>手机号</th>
                <th>TTS Token</th>
                <th>Token 上限</th>
                <th>模型训练</th>
                <th>训练上限</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in usageReport" :key="row.user_id">
                <td class="mono">{{ shortId(row.user_id) }}</td>
                <td>{{ row.phone }}</td>
                <td>
                  <QuotaUsageMeters
                    :quota="{
                      chars_used: row.chars_used,
                      chars_remaining: row.chars_remaining,
                      monthly_char_limit: row.monthly_char_limit,
                      trainings_used: 0,
                      trainings_remaining: 0,
                      monthly_train_limit: 1,
                    }"
                    layout="cell"
                    metric="chars"
                    :show-reset="false"
                  />
                </td>
                <td class="mono">{{ formatTokenVolumeWithUnit(row.monthly_char_limit) }}</td>
                <td>
                  <QuotaUsageMeters
                    :quota="{
                      chars_used: 0,
                      chars_remaining: 0,
                      monthly_char_limit: 1,
                      trainings_used: row.trainings_used,
                      trainings_remaining: row.trainings_remaining,
                      monthly_train_limit: row.monthly_train_limit,
                    }"
                    layout="cell"
                    metric="train"
                    :show-reset="false"
                  />
                </td>
                <td>{{ row.monthly_train_limit }}</td>
                <td>
                  <button type="button" class="text-action" @click="openQuotaEdit(row)">调整限额</button>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-else class="hint">本月暂无用量记录</p>
        </div>
      </RackPanel>

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
        <PageActionLink :badge="pendingConsents.length" @click="openModal('consents')">授权书审核</PageActionLink>
        <PageActionLink :badge="inviteCodes.length + waitlistEntries.length" @click="openModal('invites')">上架邀请码</PageActionLink>
        <PageActionLink :badge="complaints.length" @click="openModal('complaints')">侵权投诉</PageActionLink>
        <PageActionLink :badge="kycPending.length" @click="openModal('kyc')">实名审核</PageActionLink>
        <PageActionLink :badge="payouts.length" @click="openModal('payouts')">卖家提现</PageActionLink>
        <PageActionLink v-if="isLabsEnabled()" @click="openModal('payments')">支付订单</PageActionLink>
        <PageActionLink v-if="isLabsEnabled()" @click="router.push('/developer')">开发者 API</PageActionLink>
        <PageActionLink @click="openWebhooksModal">Webhook 投递</PageActionLink>
      </PageActionBar>
    </PageSurface>

    <AppModal :open="activeModal === 'webhooks'" label="Open API" title="Webhook 投递审计" wide @close="closeModal">
      <ul v-if="webhookDeliveries.length" class="grant-list">
        <li v-for="d in webhookDeliveries" :key="d.delivery_id">
          <span>
            <span :class="webhookStatusClass(d.status)">{{ d.status }}</span>
            · {{ d.channel }}
            · {{ d.attempts }}/{{ d.max_attempts }}
            <span class="mono"> · {{ d.target_url.slice(0, 48) }}{{ d.target_url.length > 48 ? "…" : "" }}</span>
            <span v-if="d.last_error" class="admin-table__err"> · {{ d.last_error.slice(0, 60) }}</span>
          </span>
        </li>
      </ul>
      <p v-else class="hint">暂无 Webhook 投递记录（Open API Job 完成后写入）</p>
    </AppModal>

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

    <AppModal :open="activeModal === 'consents'" label="合规" title="待审授权书" wide @close="closeModal">
      <ul v-if="pendingConsents.length" class="grant-list">
        <li v-for="c in pendingConsents" :key="c.consent_id">
          <span>
            {{ c.voice_name }} · owner {{ shortId(c.owner_user_id) }}
            · voice {{ shortId(c.voice_id) }}
          </span>
          <span class="row-actions">
            <button class="btn btn--primary btn--sm" @click="onApproveConsent(c.consent_id)">通过</button>
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <button class="text-action text-action--danger" @click="openConsentReject(c.consent_id)">驳回</button>
          </span>
        </li>
      </ul>
      <p v-else class="hint">暂无待审授权书（可在 Studio 上传后关闭 CONSENT_AUTO_APPROVE 测试）</p>
    </AppModal>

    <AppModal :open="activeModal === 'invites'" label="音色馆" title="上架邀请码与候补" wide @close="closeModal">
      <h3 class="admin-section-title">候补名单</h3>
      <ul v-if="waitlistEntries.length" class="grant-list">
        <li v-for="w in waitlistEntries" :key="w.waitlist_id">
          <span>
            <span class="mono">{{ shortId(w.user_id) }}</span>
            <span v-if="w.phone"> · {{ w.phone }}</span>
            <span v-if="w.contact"> · {{ w.contact }}</span>
            <span v-if="w.note"> · {{ w.note }}</span>
          </span>
          <span class="row-actions">
            <button class="btn btn--primary btn--sm" type="button" @click="onIssueWaitlist(w.waitlist_id)">
              一键发码
            </button>
          </span>
        </li>
      </ul>
      <p v-else class="hint">暂无待处理候补</p>

      <h3 class="admin-section-title">邀请码</h3>
      <ul v-if="inviteCodes.length" class="grant-list">
        <li v-for="ic in inviteCodes" :key="ic.invite_code_id">
          <span>
            <strong>{{ ic.code }}</strong>
            · {{ ic.used_count }}/{{ ic.max_uses }}
            <span v-if="ic.note"> · {{ ic.note }}</span>
            <span v-if="ic.revoked_at" class="pill pill--danger">已撤销</span>
          </span>
        </li>
      </ul>
      <p v-else class="hint">暂无邀请码</p>
      <div class="form-grid admin-invite-form">
        <label>
          邀请码
          <input v-model="inviteCode" placeholder="PHONIA-CREATOR-02" />
        </label>
        <label>
          可用次数
          <input v-model.number="inviteMaxUses" type="number" min="1" />
        </label>
        <label>
          有效天数（可选）
          <input v-model="inviteExpiresDays" type="number" min="1" placeholder="30" />
        </label>
        <label class="form-grid__full">
          备注
          <input v-model="inviteNote" placeholder="内测创作者批次 A" />
        </label>
      </div>
      <template #footer>
        <button class="btn btn--ghost btn--sm" type="button" @click="closeModal">关闭</button>
        <button class="btn btn--primary btn--sm" type="button" @click="onCreateInvite">创建邀请码</button>
      </template>
    </AppModal>

    <AppModal
      :open="activeModal === 'consentReject'"
      label="驳回"
      title="驳回授权书"
      @close="closeModal"
    >
      <label>
        驳回原因
        <textarea v-model="consentRejectReason" rows="4" />
      </label>
      <template #footer>
        <button class="btn btn--ghost btn--sm" type="button" @click="closeModal">取消</button>
        <button class="btn btn--primary btn--sm" type="button" @click="onRejectConsent">确认驳回</button>
      </template>
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

    <AppModal
      :open="activeModal === 'quota'"
      label="配额"
      :title="quotaEditUser ? `调整限额 · ${quotaEditUser.phone}` : '调整限额'"
      @close="closeModal"
    >
      <p v-if="quotaEditUser" class="hint">
        本月已用：TTS Token {{ formatTokenVolumeWithUnit(quotaEditUser.chars_used) }} · 模型训练 {{ quotaEditUser.trainings_used }} 次
      </p>
      <div class="admin-quota-tiers">
        <span class="field-label">套餐档位</span>
        <div class="admin-quota-tiers__row">
          <button
            v-for="tier in QUOTA_TIERS"
            :key="tier.id"
            type="button"
            class="btn btn--ghost btn--sm"
            :title="tier.hint"
            @click="applyQuotaTier(tier)"
          >
            {{ tier.label }}
          </button>
        </div>
        <p class="hint">点选档位填入下方数值，可再手动微调后保存。</p>
      </div>
      <label>
        月度 TTS Token 上限
        <input v-model="quotaCharLimit" type="number" min="0" step="1000" />
      </label>
      <label>
        月度训练次数上限
        <input v-model="quotaTrainLimit" type="number" min="0" step="1" />
      </label>
      <template #footer>
        <button class="btn btn--ghost btn--sm" type="button" :disabled="quotaSaving" @click="closeModal">取消</button>
        <button class="btn btn--primary btn--sm" type="button" :disabled="quotaSaving" @click="saveQuotaEdit">
          {{ quotaSaving ? "保存中…" : "保存" }}
        </button>
      </template>
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

.admin-quota-tiers {
  margin-bottom: 1rem;
}

.admin-quota-tiers__row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.35rem;
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

.admin-section-title {
  margin: 16px 0 8px;
  font-size: 13px;
  font-family: var(--font-mono);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-brushed-dark);
}

.admin-section-title:first-child {
  margin-top: 0;
}
</style>
