<script setup lang="ts">
import { LICENSE_TYPES, type Authorization, type CatalogEntry, type VoiceGrant, type VoiceSummary } from "@/api/catalog";
import type { PublishEligibility, SellerAuthorizationStats } from "@/api/marketplace";
import type { SellerWallet } from "@/api/settlement";
import type { VoiceVersionSummary } from "@/api/library";
import AppModal from "@/components/AppModal.vue";
import type { CatalogManageModal, CheckoutSummary } from "@/modules/voice/composables/useCatalogManage";
import { catalogStatusLabel, shortUserId } from "@/utils/catalogDisplay";

defineProps<{
  activeModal: CatalogManageModal;
  loading: boolean;
  selectedEntry: CatalogEntry | null;
  ownedVersions: VoiceVersionSummary[];
  mySubmissions: CatalogEntry[];
  pendingReview: CatalogEntry[];
  myAuthorizations: Authorization[];
  issuedAuthorizations: Authorization[];
  sellerWallet: SellerWallet | null;
  sellerStats: SellerAuthorizationStats | null;
  myVoices: VoiceSummary[];
  issuedGrants: VoiceGrant[];
  receivedGrants: VoiceGrant[];
  publishVersionId: string;
  publishTitle: string;
  publishDescription: string;
  publishTags: string;
  publishDemoText: string;
  publishLicenseType: string;
  publishPriceYuan: string;
  publishIncludedChars: number;
  publishProhibited: string[];
  payoutAmountYuan: string;
  complaintText: string;
  grantVoiceId: string;
  granteeUserId: string;
  checkoutSummary: CheckoutSummary | null;
  publishEligibility: PublishEligibility | null;
  inviteCode: string;
  waitlistContact: string;
  waitlistNote: string;
  versionOptionLabel: (v: VoiceVersionSummary) => string;
  devUserPresets: ReadonlyArray<{ readonly id: string; readonly label: string }>;
  prohibitedDomainOptions: readonly string[];
}>();

const emit = defineEmits<{
  close: [];
  publish: [];
  requestPayout: [];
  submitComplaint: [];
  grant: [];
  revokeGrant: [grantId: string];
  approve: [catalogId: string];
  reject: [catalogId: string];
  redeemInvite: [];
  joinWaitlist: [];
  exportCertificate: [authId: string];
  toggleProhibited: [domain: string];
  dismissCheckout: [];
  goSynthAfterCheckout: [];
  "update:publishVersionId": [v: string];
  "update:publishTitle": [v: string];
  "update:publishDescription": [v: string];
  "update:publishTags": [v: string];
  "update:publishDemoText": [v: string];
  "update:publishLicenseType": [v: string];
  "update:publishPriceYuan": [v: string];
  "update:publishIncludedChars": [v: number];
  "update:payoutAmountYuan": [v: string];
  "update:complaintText": [v: string];
  "update:grantVoiceId": [v: string];
  "update:granteeUserId": [v: string];
  "update:inviteCode": [v: string];
  "update:waitlistContact": [v: string];
  "update:waitlistNote": [v: string];
  goLibrary: [];
}>();
</script>

<template>
  <AppModal :open="activeModal === 'publish'" label="发布" title="发布到音色馆" wide @close="emit('close')">
    <p class="hint modal-hint">仅音色所有者可发布；需邀请码 + 相似度测评通过（quality_pass）。</p>
    <div
      v-if="publishEligibility && !publishEligibility.can_publish"
      class="invite-gate"
    >
      <p class="hint warn">{{ publishEligibility.message }}</p>
      <div class="form-grid">
        <label class="span-2">
          邀请码
          <input
            :value="inviteCode"
            placeholder="例如 PHONIA-CREATOR"
            @input="emit('update:inviteCode', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <div class="span-2 row-actions">
          <button class="btn btn--primary btn--sm" type="button" @click="emit('redeemInvite')">兑换邀请码</button>
        </div>
        <label>
          联系方式（候补）
          <input
            :value="waitlistContact"
            placeholder="手机 / 微信"
            @input="emit('update:waitlistContact', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <label>
          备注
          <input
            :value="waitlistNote"
            placeholder="配音师简介 / 作品链接"
            @input="emit('update:waitlistNote', ($event.target as HTMLInputElement).value)"
          />
        </label>
        <div class="span-2">
          <button class="btn btn--ghost btn--sm" type="button" @click="emit('joinWaitlist')">
            {{ publishEligibility.on_waitlist ? "更新候补信息" : "加入候补名单" }}
          </button>
        </div>
      </div>
    </div>
    <p v-if="!ownedVersions.length && !loading" class="hint warn">
      暂无可用版本。请先到
      <router-link to="/library">音色库</router-link>
      导入 cloud-004 权重后再发布。
    </p>
    <div v-else-if="publishEligibility?.can_publish !== false" class="form-grid">
      <label class="span-2">
        我的版本
        <select :value="publishVersionId" @change="emit('update:publishVersionId', ($event.target as HTMLSelectElement).value)">
          <option disabled value="">请选择版本</option>
          <option v-for="v in ownedVersions" :key="v.voice_version_id" :value="v.voice_version_id">
            {{ versionOptionLabel(v) }}
          </option>
        </select>
      </label>
      <label>
        展示标题
        <input
          :value="publishTitle"
          placeholder="例如：蛊真人·龙宫"
          @input="emit('update:publishTitle', ($event.target as HTMLInputElement).value)"
        />
      </label>
      <label>
        标签（逗号分隔）
        <input
          :value="publishTags"
          placeholder="短剧, 男声, 反派"
          @input="emit('update:publishTags', ($event.target as HTMLInputElement).value)"
        />
      </label>
      <label class="span-2">
        简介
        <textarea
          :value="publishDescription"
          rows="2"
          @input="emit('update:publishDescription', ($event.target as HTMLTextAreaElement).value)"
        />
      </label>
      <label>
        试听样音台词
        <input
          :value="publishDemoText"
          placeholder="审核通过后将自动预生成试听 URL"
          @input="emit('update:publishDemoText', ($event.target as HTMLInputElement).value)"
        />
      </label>
      <label>
        授权类型
        <select
          :value="publishLicenseType"
          @change="emit('update:publishLicenseType', ($event.target as HTMLSelectElement).value)"
        >
          <option v-for="lt in LICENSE_TYPES" :key="lt.id" :value="lt.id">{{ lt.label }}</option>
        </select>
      </label>
      <label>
        价格（元，0=免费公开）
        <input
          :value="publishPriceYuan"
          type="number"
          min="0"
          step="0.01"
          @input="emit('update:publishPriceYuan', ($event.target as HTMLInputElement).value)"
        />
      </label>
      <label>
        含字符额度
        <input
          :value="publishIncludedChars"
          type="number"
          min="0"
          step="1000"
          @input="emit('update:publishIncludedChars', Number(($event.target as HTMLInputElement).value))"
        />
      </label>
      <label class="span-2">
        禁止领域
        <span class="tag-chips" style="margin-top: 6px">
          <button
            v-for="d in prohibitedDomainOptions"
            :key="d"
            type="button"
            class="tag-chip"
            :class="{ 'tag-chip--active': publishProhibited.includes(d) }"
            @click="emit('toggleProhibited', d)"
          >
            {{ d }}
          </button>
        </span>
      </label>
    </div>
    <template #footer>
      <button class="btn btn--ghost btn--sm" type="button" @click="emit('close')">取消</button>
      <button
        class="btn btn--primary btn--sm"
        type="button"
        :disabled="loading || !publishVersionId || !ownedVersions.length || publishEligibility?.can_publish === false"
        @click="emit('publish')"
      >
        发布到音色馆
      </button>
    </template>
  </AppModal>

  <AppModal :open="activeModal === 'submissions'" label="记录" title="我的发布" @close="emit('close')">
    <ul class="grant-list">
      <li v-for="s in mySubmissions" :key="s.catalog_id">
        <span>{{ s.title }} · {{ catalogStatusLabel(s.status) }}</span>
      </li>
    </ul>
  </AppModal>

  <AppModal :open="activeModal === 'review'" label="运营" title="审核队列" @close="emit('close')">
    <p class="hint modal-hint">当前以调试用户 C（运营）身份登录。请先在右上角切换用户。</p>
    <ul v-if="pendingReview.length" class="grant-list">
      <li v-for="p in pendingReview" :key="p.catalog_id">
        <span>
          {{ p.title }} · {{ p.voice_name }}
          <template v-if="p.similarity_score != null">
            · 相似度 {{ (p.similarity_score * 100).toFixed(1) }}%
          </template>
          <template v-if="p.quality_pass != null">
            · {{ p.quality_pass ? "测评通过" : "测评未达标" }}
          </template>
        </span>
        <span class="row-actions">
          <button class="btn btn--primary btn--sm" @click="emit('approve', p.catalog_id)">通过</button>
          <span class="row-actions__sep" aria-hidden="true">·</span>
          <button class="text-action text-action--danger" @click="emit('reject', p.catalog_id)">驳回</button>
        </span>
      </li>
    </ul>
    <p v-else class="hint">还没有待审核条目</p>
  </AppModal>

  <AppModal :open="activeModal === 'authorizations'" label="购买" title="我的音色授权" @close="emit('close')">
    <ul class="grant-list">
      <li v-for="a in myAuthorizations" :key="a.authorization_id">
        <span>
          {{ a.voice_title }} · {{ a.status }} · 剩余 {{ a.char_quota_remaining.toLocaleString() }} 字
        </span>
        <span class="row-actions">
          <button class="text-action" @click="emit('exportCertificate', a.authorization_id)">导出 PDF</button>
          <span class="row-actions__sep" aria-hidden="true">·</span>
          <router-link class="text-action" :to="`/verify/${a.authorization_id}`">验真</router-link>
        </span>
      </li>
    </ul>
  </AppModal>

  <AppModal
    v-if="sellerWallet"
    :open="activeModal === 'wallet'"
    label="结算"
    title="卖家钱包"
    @close="emit('close')"
  >
    <p v-if="sellerStats" class="hint modal-hint">
      授权统计：成交 {{ sellerStats.total_sales }} 笔 · 有效授权 {{ sellerStats.active_authorizations }} ·
      已用 {{ sellerStats.total_chars_used.toLocaleString() }} /
      {{ sellerStats.total_chars_quota.toLocaleString() }} 字
    </p>
    <p class="hint modal-hint">
      可提现 ¥{{ (sellerWallet.balance_cents / 100).toFixed(2) }} · 待打款 ¥{{
        (sellerWallet.pending_payout_cents / 100).toFixed(2)
      }}
      · 累计 ¥{{ (sellerWallet.total_earned_cents / 100).toFixed(2) }}
      · 费率 {{ (sellerWallet.platform_fee_bps / 100).toFixed(1) }}%
    </p>
    <div class="form-grid">
      <label>
        提现金额（元，最低 ¥{{ (sellerWallet.min_payout_cents / 100).toFixed(0) }}）
        <input
          :value="payoutAmountYuan"
          type="number"
          min="0"
          step="0.01"
          placeholder="100"
          @input="emit('update:payoutAmountYuan', ($event.target as HTMLInputElement).value)"
        />
      </label>
    </div>
    <template #footer>
      <button class="btn btn--ghost btn--sm" type="button" @click="emit('close')">取消</button>
      <button class="btn btn--primary btn--sm" type="button" @click="emit('requestPayout')">申请提现</button>
    </template>
  </AppModal>

  <AppModal :open="activeModal === 'sales'" label="销售" title="我售出的授权" @close="emit('close')">
    <ul class="grant-list">
      <li v-for="a in issuedAuthorizations" :key="a.authorization_id">
        <span>
          {{ a.voice_title }} → {{ shortUserId(a.buyer_user_id) }} · {{ a.status }} ·
          已用 {{ a.char_quota_used.toLocaleString() }}/{{ a.char_quota_total.toLocaleString() }} 字
        </span>
      </li>
    </ul>
  </AppModal>

  <AppModal :open="activeModal === 'complaint'" label="合规" title="侵权投诉" @close="emit('close')">
    <p class="hint modal-hint">发现侵权可提交工单，运营核实后将下架并撤销购买授权。</p>
    <label class="span-2">
      投诉说明
      <textarea
        :value="complaintText"
        rows="4"
        placeholder="请描述侵权情况（至少 10 字）"
        @input="emit('update:complaintText', ($event.target as HTMLTextAreaElement).value)"
      />
    </label>
    <p v-if="!selectedEntry" class="hint warn">请先在音色馆选中要投诉的条目</p>
    <template #footer>
      <button class="btn btn--ghost btn--sm" type="button" @click="emit('close')">取消</button>
      <button class="btn btn--primary btn--sm" type="button" :disabled="!selectedEntry" @click="emit('submitComplaint')">
        提交投诉
      </button>
    </template>
  </AppModal>

  <AppModal :open="activeModal === 'grant'" label="授权" title="单独授权" wide @close="emit('close')">
    <p class="hint modal-hint">
      不公开上架时，可单独授权他人使用。开发模式请在右上角切换调试用户 A/B 进行验证。
    </p>
    <div class="form-grid">
      <label class="field">
        <span>我的音色</span>
        <select :value="grantVoiceId" @change="emit('update:grantVoiceId', ($event.target as HTMLSelectElement).value)">
          <option disabled value="">请选择音色</option>
          <option v-for="v in myVoices" :key="v.voice_id" :value="v.voice_id">
            {{ v.name }}（{{ v.version_count }} 个版本）
          </option>
        </select>
      </label>
      <label class="field">
        <span>被授权用户 ID</span>
        <input
          :value="granteeUserId"
          placeholder="UUID"
          @input="emit('update:granteeUserId', ($event.target as HTMLInputElement).value)"
        />
      </label>
    </div>
    <div class="preset-row">
      <span class="preset-row__label">快捷填入</span>
      <div class="preset-row__chips">
        <button
          v-for="u in devUserPresets"
          :key="u.id"
          type="button"
          class="prompt-chip"
          @click="emit('update:granteeUserId', u.id)"
        >
          {{ u.label }}
        </button>
      </div>
    </div>
    <h3 class="subhead subhead--spaced">我发出的授权</h3>
    <ul v-if="issuedGrants.length" class="grant-list">
      <li v-for="g in issuedGrants" :key="g.grant_id">
        <span>{{ g.voice_name }} → {{ shortUserId(g.grantee_user_id) }}</span>
        <button class="text-action text-action--danger" @click="emit('revokeGrant', g.grant_id)">撤销</button>
      </li>
    </ul>
    <p v-else class="hint">还没有发出的授权</p>
    <h3 class="subhead subhead--spaced">我收到的授权</h3>
    <ul v-if="receivedGrants.length" class="grant-list">
      <li v-for="g in receivedGrants" :key="g.grant_id">
        <span>{{ g.voice_name }}（来自 {{ shortUserId(g.granter_user_id) }}）</span>
        <button class="text-action" @click="emit('goLibrary')">去音色库</button>
      </li>
    </ul>
    <p v-else class="hint">暂无收到的授权</p>
    <template #footer>
      <button class="btn btn--ghost btn--sm" type="button" @click="emit('close')">取消</button>
      <button class="btn btn--primary btn--sm" type="button" :disabled="loading || !grantVoiceId" @click="emit('grant')">
        授权合成
      </button>
    </template>
  </AppModal>

  <AppModal
    :open="activeModal === 'checkout' && !!checkoutSummary"
    label="支付"
    :title="checkoutSummary?.status === 'pending' ? '扫码支付' : '购买成功'"
    @close="emit('dismissCheckout')"
  >
    <template v-if="checkoutSummary">
      <p class="checkout-status">
        <strong>{{ checkoutSummary.voiceTitle }}</strong>
        <span
          class="pill"
          :class="checkoutSummary.status === 'paid' ? 'pill--ok' : 'pill--warn'"
        >
          {{ checkoutSummary.status === 'paid' ? '已授权' : '待支付' }}
        </span>
      </p>
      <dl class="checkout-dl">
        <div><dt>金额</dt><dd>{{ checkoutSummary.priceLabel }}</dd></div>
        <div><dt>订单号</dt><dd class="mono">{{ checkoutSummary.orderRef }}</dd></div>
        <div v-if="checkoutSummary.provider">
          <dt>渠道</dt>
          <dd>{{ checkoutSummary.provider }}</dd>
        </div>
        <div v-if="checkoutSummary.authorizationId">
          <dt>授权 ID</dt>
          <dd class="mono">{{ checkoutSummary.authorizationId }}</dd>
        </div>
      </dl>

      <template v-if="checkoutSummary.status === 'pending' && checkoutSummary.qrCodeUrl">
        <p class="hint">请使用支付宝沙箱 App 扫描下方二维码完成付款。支付成功后本页将自动刷新。</p>
        <div class="checkout-qr">
          <img
            :src="`https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(checkoutSummary.qrCodeUrl)}`"
            alt="支付宝付款码"
            width="220"
            height="220"
          />
        </div>
        <p class="row-actions checkout-links">
          <a
            class="text-action text-action--accent"
            :href="checkoutSummary.qrCodeUrl"
            target="_blank"
            rel="noopener noreferrer"
          >
            在浏览器打开付款链接
          </a>
        </p>
      </template>
      <template v-else-if="checkoutSummary.status === 'pending'">
        <p class="hint">订单已创建，等待支付确认…</p>
      </template>
      <template v-else>
        <p class="hint">支付已确认。你现在可以试听合成、导出 PDF 或在线验真。</p>
        <p v-if="checkoutSummary.authorizationId" class="row-actions checkout-links">
          <router-link class="text-action text-action--accent" :to="`/verify/${checkoutSummary.authorizationId}`">
            授权验真
          </router-link>
        </p>
      </template>
    </template>
    <template #footer>
      <button class="btn btn--ghost btn--sm" type="button" @click="emit('dismissCheckout')">关闭</button>
      <button
        v-if="checkoutSummary?.status === 'paid'"
        class="btn btn--primary btn--sm"
        type="button"
        @click="emit('goSynthAfterCheckout')"
      >
        立即试听合成
      </button>
    </template>
  </AppModal>
</template>

<style scoped>
.checkout-status {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 12px;
  font-size: 1.05rem;
}

.checkout-dl {
  margin: 0 0 12px;
  display: grid;
  gap: 8px;
}

.checkout-dl div {
  display: flex;
  gap: 12px;
}

.checkout-dl dt {
  min-width: 4em;
  color: var(--color-ink-muted);
  font-size: 0.85rem;
}

.checkout-dl dd {
  margin: 0;
}

.mono {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.85rem;
}

.checkout-links {
  margin: 0 0 4px;
}

.checkout-qr {
  display: flex;
  justify-content: center;
  margin: 12px 0;
  padding: 12px;
  background: #fff;
  border-radius: 8px;
}
</style>
