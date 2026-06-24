import { computed, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError } from "@/api/client";
import {
  approveCatalogEntry,
  createVoiceGrant,
  DEV_ADMIN_USER_ID,
  DEV_USER_PRESETS,
  fetchIssuedGrantsOptional,
  fetchIssuedAuthorizations,
  fetchMyAuthorizations,
  fetchMyCatalogSubmissions,
  fetchMyVoices,
  fetchPendingCatalog,
  fetchReceivedGrants,
  getDevUserId,
  PROHIBITED_DOMAIN_OPTIONS,
  publishToCatalog,
  purchaseCatalogWithCheckout,
  fetchPaymentOrder,
  regenerateCatalogDemo,
  rejectCatalogEntry,
  revokeVoiceGrant,
  submitComplaint,
  type Authorization,
  type VoiceGrant,
  type VoiceSummary,
} from "@/api/catalog";
import { authorizationCertificatePdfUrl } from "@/api/quality";
import {
  catalogDemoDownloadUrl,
  catalogVoicePackUrl,
  downloadCatalogAsset,
} from "@/api/social";
import { fetchSellerWallet, requestSellerPayout, type SellerWallet } from "@/api/settlement";
import {
  fetchPublishEligibility,
  fetchSellerAuthorizationStats,
  joinMarketplaceWaitlist,
  redeemMarketplaceInvite,
  type PublishEligibility,
  type SellerAuthorizationStats,
} from "@/api/marketplace";
import { fetchVoiceVersions, type VoiceVersionSummary } from "@/api/library";
import { formatApiError } from "@/utils/apiErrors";
import { parseCatalogTags } from "@/utils/catalogDisplay";
import type { CatalogBrowse } from "@/modules/voice/composables/useCatalogBrowse";

export type CatalogManageModal =
  | ""
  | "publish"
  | "submissions"
  | "review"
  | "authorizations"
  | "wallet"
  | "sales"
  | "complaint"
  | "grant"
  | "checkout";

export type CheckoutSummary = {
  voiceTitle: string;
  priceLabel: string;
  orderRef: string;
  catalogId: string;
  orderId?: string;
  status: "pending" | "paid";
  provider?: string;
  authorizationId?: string;
  qrCodeUrl?: string;
  checkoutUrl?: string;
};

function pickPreferredVersionId(versions: VoiceVersionSummary[]): string {
  const preferred = versions.find(
    (v) => (v.label && /004/i.test(v.label)) || /004/.test(v.voice_name),
  );
  return preferred?.voice_version_id ?? versions[0]?.voice_version_id ?? "";
}

function versionOptionLabel(v: VoiceVersionSummary): string {
  const label = v.label ? ` (${v.label})` : "";
  const imported = v.imported ? " · 已导入" : "";
  return `${v.voice_name} v${v.version}${label}${imported}`;
}

export function useCatalogManage(browse: CatalogBrowse) {
  const router = useRouter();

  const mySubmissions = ref<Awaited<ReturnType<typeof fetchMyCatalogSubmissions>>>([]);
  const pendingReview = ref<Awaited<ReturnType<typeof fetchPendingCatalog>>>([]);
  const myVersions = ref<VoiceVersionSummary[]>([]);
  const myVoices = ref<VoiceSummary[]>([]);
  const issuedGrants = ref<VoiceGrant[]>([]);
  const receivedGrants = ref<VoiceGrant[]>([]);
  const myAuthorizations = ref<Authorization[]>([]);
  const issuedAuthorizations = ref<Authorization[]>([]);
  const sellerWallet = ref<SellerWallet | null>(null);
  const sellerStats = ref<SellerAuthorizationStats | null>(null);

  const publishVersionId = ref("");
  const publishTitle = ref("蛊真人·龙宫");
  const publishDescription = ref("平台精选：004 云端微调音色");
  const publishTags = ref("短剧, 男声, 反派");
  const publishDemoText = ref("方源，你给我出来！");
  const publishLicenseType = ref("personal_non_commercial");
  const publishPriceYuan = ref("0");
  const publishIncludedChars = ref(50000);
  const publishProhibited = ref<string[]>([]);
  const payoutAmountYuan = ref("");
  const complaintText = ref("");
  const grantVoiceId = ref("");
  const granteeUserId = ref<string>(DEV_USER_PRESETS[1].id);
  const checkoutSummary = ref<CheckoutSummary | null>(null);
  const publishEligibility = ref<PublishEligibility | null>(null);
  const inviteCode = ref("");
  const waitlistContact = ref("");
  const waitlistNote = ref("");

  let paymentPollTimer: ReturnType<typeof setInterval> | null = null;

  const activeModal = ref<CatalogManageModal>("");

  const ownedVersions = computed(() => myVersions.value.filter((v) => !v.granted));
  const isAdmin = computed(() => getDevUserId() === DEV_ADMIN_USER_ID);

  function openModal(id: CatalogManageModal) {
    activeModal.value = id;
  }

  function closeModal() {
    activeModal.value = "";
  }

  async function loadPublishEligibility() {
    try {
      publishEligibility.value = await fetchPublishEligibility();
    } catch {
      publishEligibility.value = null;
    }
  }

  async function onRedeemInvite() {
    browse.error.value = "";
    browse.success.value = "";
    const code = inviteCode.value.trim();
    if (!code) {
      browse.error.value = "请输入邀请码";
      return;
    }
    try {
      const res = await redeemMarketplaceInvite(code);
      browse.success.value = res.message;
      inviteCode.value = "";
      await loadPublishEligibility();
    } catch (e) {
      browse.error.value = formatApiError(e);
    }
  }

  async function onJoinWaitlist() {
    browse.error.value = "";
    browse.success.value = "";
    try {
      const res = await joinMarketplaceWaitlist({
        contact: waitlistContact.value.trim(),
        note: waitlistNote.value.trim(),
      });
      browse.success.value = res.message;
      await loadPublishEligibility();
    } catch (e) {
      browse.error.value = formatApiError(e);
    }
  }

  async function reload() {
    browse.loading.value = true;
    browse.error.value = "";
    try {
      const [versions, voices, issued, received, mine, auths, sold] = await Promise.all([
        fetchVoiceVersions(),
        fetchMyVoices(),
        fetchIssuedGrantsOptional(),
        fetchReceivedGrants(),
        fetchMyCatalogSubmissions(),
        fetchMyAuthorizations(),
        fetchIssuedAuthorizations(),
      ]);
      mySubmissions.value = mine;
      myAuthorizations.value = auths;
      issuedAuthorizations.value = sold;
      await browse.loadCatalog();
      if (isAdmin.value) {
        try {
          pendingReview.value = await fetchPendingCatalog();
        } catch (e) {
          if (!(e instanceof ApiError && e.status === 403)) throw e;
          pendingReview.value = [];
        }
      } else {
        pendingReview.value = [];
      }
      myVersions.value = versions;
      myVoices.value = voices;
      issuedGrants.value = issued;
      receivedGrants.value = received;
      try {
        sellerWallet.value = await fetchSellerWallet();
        sellerStats.value = await fetchSellerAuthorizationStats();
      } catch {
        sellerWallet.value = null;
        sellerStats.value = null;
      }
      if (!grantVoiceId.value && voices.length) {
        grantVoiceId.value = voices[0].voice_id;
      }
      if (!publishVersionId.value && ownedVersions.value.length) {
        publishVersionId.value = pickPreferredVersionId(ownedVersions.value);
      }
      await loadPublishEligibility();
    } catch (e) {
      browse.error.value = formatApiError(e);
    } finally {
      browse.loading.value = false;
    }
  }

  async function onPublish() {
    browse.error.value = "";
    browse.success.value = "";
    const title = publishTitle.value.trim();
    if (!publishVersionId.value) {
      browse.error.value = "请先选择要发布的音色版本（需先在音色库导入 004）";
      return;
    }
    if (!title) {
      browse.error.value = "请填写展示标题";
      return;
    }
    try {
      const entry = await publishToCatalog({
        voice_version_id: publishVersionId.value,
        title,
        description: publishDescription.value.trim(),
        tags: parseCatalogTags(publishTags.value),
        featured: true,
        demo_text: publishDemoText.value.trim(),
        license_type: publishLicenseType.value,
        price_cents: Math.round(parseFloat(publishPriceYuan.value || "0") * 100),
        billing_unit: "per_1k_chars",
        included_chars: publishIncludedChars.value,
        prohibited_domains: publishProhibited.value,
      });
      browse.success.value =
        entry.status === "published"
          ? `已发布「${title}」到音色馆`
          : `已提交「${title}」审核，请等待运营放行`;
      closeModal();
      await reload();
    } catch (e) {
      browse.error.value = formatApiError(e);
    }
  }

  async function onRequestPayout() {
    if (!sellerWallet.value) return;
    const cents = Math.round(parseFloat(payoutAmountYuan.value || "0") * 100);
    if (!cents) {
      browse.error.value = "请输入提现金额";
      return;
    }
    browse.error.value = "";
    try {
      await requestSellerPayout(cents);
      browse.success.value = `提现申请已提交 ¥${(cents / 100).toFixed(2)}`;
      payoutAmountYuan.value = "";
      closeModal();
      await reload();
    } catch (e) {
      browse.error.value = formatApiError(e);
    }
  }

  function stopPaymentPoll() {
    if (paymentPollTimer) {
      clearInterval(paymentPollTimer);
      paymentPollTimer = null;
    }
  }

  async function refreshPaymentOrder(orderId: string) {
    const order = await fetchPaymentOrder(orderId);
    if (order.status !== "paid" || !checkoutSummary.value) {
      return;
    }
    stopPaymentPoll();
    checkoutSummary.value = {
      ...checkoutSummary.value,
      status: "paid",
      authorizationId: order.authorization_id ?? undefined,
      orderRef: order.provider_ref,
    };
    browse.success.value = `已购买「${checkoutSummary.value.voiceTitle}」`;
    await reload();
  }

  function startPaymentPoll(orderId: string) {
    stopPaymentPoll();
    void refreshPaymentOrder(orderId);
    paymentPollTimer = setInterval(() => {
      void refreshPaymentOrder(orderId);
    }, 3000);
  }

  onUnmounted(() => {
    stopPaymentPoll();
  });

  async function onPurchaseSelected() {
    const target = browse.selectedEntry.value;
    if (!target) return;
    browse.error.value = "";
    browse.success.value = "";
    try {
      const result = await purchaseCatalogWithCheckout(target.catalog_id, target.price_cents);
      const authId =
        "authorization_id" in result && result.authorization_id
          ? String(result.authorization_id)
          : undefined;
      const orderRef =
        "provider_ref" in result && result.provider_ref
          ? result.provider_ref
          : authId ?? ("order_id" in result ? result.order_id : "待支付");
      const isPaid = result.status === "paid";
      checkoutSummary.value = {
        voiceTitle: target.title,
        priceLabel: `¥${(target.price_cents / 100).toFixed(2)}`,
        orderRef: String(orderRef),
        catalogId: target.catalog_id,
        orderId: result.order_id,
        status: isPaid ? "paid" : "pending",
        provider: result.provider,
        authorizationId: authId,
        qrCodeUrl: result.qr_code_url ?? undefined,
        checkoutUrl: result.checkout_url ?? undefined,
      };
      if (isPaid) {
        browse.success.value = `已购买「${target.title}」`;
      } else {
        browse.success.value = "";
        startPaymentPoll(result.order_id);
      }
      activeModal.value = "checkout";
      if (isPaid) {
        await reload();
      }
    } catch (e) {
      browse.error.value = formatApiError(e);
    }
  }

  async function onDownloadDemoSelected() {
    const target = browse.selectedEntry.value;
    if (!target) return;
    try {
      await downloadCatalogAsset(catalogDemoDownloadUrl(target.catalog_id), `${target.title}_demo.wav`);
    } catch (e) {
      browse.error.value = formatApiError(e);
    }
  }

  async function onDownloadPackSelected() {
    const target = browse.selectedEntry.value;
    if (!target) return;
    try {
      await downloadCatalogAsset(catalogVoicePackUrl(target.catalog_id), `${target.title}_pack.zip`);
    } catch (e) {
      browse.error.value = formatApiError(e);
    }
  }

  async function onExportCertificate(authId: string) {
    browse.error.value = "";
    try {
      const url = authorizationCertificatePdfUrl(authId);
      const headers: Record<string, string> = {};
      const token = localStorage.getItem("access_token");
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      } else if (localStorage.getItem("dev_mode") === "1") {
        headers["X-User-Id"] = getDevUserId();
      }
      const res = await fetch(url, { headers });
      if (!res.ok) throw new Error(`PDF export failed (${res.status})`);
      const blob = await res.blob();
      const obj = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = obj;
      a.download = `authorization-${authId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(obj);
      browse.success.value = "PDF 授权凭证已下载";
    } catch (e) {
      browse.error.value = e instanceof Error ? e.message : formatApiError(e);
    }
  }

  function verifyUrl(authId: string): string {
    return `/verify/${authId}`;
  }

  async function onSubmitComplaint() {
    const target = browse.selectedEntry.value;
    const text = complaintText.value.trim();
    if (!target || text.length < 10) {
      browse.error.value = "请选中音色并填写至少 10 字的投诉说明";
      return;
    }
    browse.error.value = "";
    try {
      await submitComplaint({
        catalog_id: target.catalog_id,
        description: text,
        target_url: window.location.href,
      });
      complaintText.value = "";
      browse.success.value = "投诉已提交，运营将在 72h 内处理";
      closeModal();
    } catch (e) {
      browse.error.value = formatApiError(e);
    }
  }

  function toggleProhibited(domain: string) {
    const idx = publishProhibited.value.indexOf(domain);
    if (idx >= 0) publishProhibited.value.splice(idx, 1);
    else publishProhibited.value.push(domain);
  }

  async function onGrant() {
    browse.error.value = "";
    browse.success.value = "";
    if (!grantVoiceId.value || !granteeUserId.value.trim()) {
      browse.error.value = "请选择音色并填写被授权用户 ID";
      return;
    }
    try {
      await createVoiceGrant(grantVoiceId.value, granteeUserId.value.trim());
      browse.success.value = "授权已创建";
      closeModal();
      await reload();
    } catch (e) {
      browse.error.value = formatApiError(e);
    }
  }

  async function onRevokeGrant(grantId: string) {
    browse.error.value = "";
    try {
      await revokeVoiceGrant(grantId);
      browse.success.value = "授权已撤销";
      await reload();
    } catch (e) {
      browse.error.value = formatApiError(e);
    }
  }

  async function onApprove(catalogId: string) {
    browse.error.value = "";
    browse.success.value = "";
    try {
      await approveCatalogEntry(catalogId);
      browse.success.value = "已通过审核";
      await reload();
    } catch (err) {
      browse.error.value = formatApiError(err);
    }
  }

  async function onReject(catalogId: string) {
    browse.error.value = "";
    browse.success.value = "";
    const reason = window.prompt("请输入驳回原因（将通知创作者）：", "素材或授权材料不符合要求");
    if (!reason?.trim()) {
      browse.error.value = "驳回必须填写原因";
      return;
    }
    try {
      await rejectCatalogEntry(catalogId, reason.trim());
      browse.success.value = "已驳回并通知创作者";
      await reload();
    } catch (err) {
      browse.error.value = formatApiError(err);
    }
  }

  async function onRegenerateDemo(catalogId: string) {
    browse.error.value = "";
    browse.success.value = "";
    try {
      await regenerateCatalogDemo(catalogId);
      browse.success.value = "已提交样音生成任务";
      await browse.loadCatalog();
    } catch (err) {
      browse.error.value = formatApiError(err);
    }
  }

  function dismissCheckout() {
    stopPaymentPoll();
    checkoutSummary.value = null;
    closeModal();
  }

  function clearPurchaseIntent() {
    const q = { ...browse.route.query };
    delete q.intent;
    browse.router.replace({ query: q });
  }

  async function maybeAutoPurchase() {
    const intent = String(browse.route.query.intent ?? "");
    if (intent !== "purchase") return;
    const entry = browse.selectedEntry.value;
    if (!entry || entry.can_use || entry.price_cents <= 0) {
      clearPurchaseIntent();
      return;
    }
    await onPurchaseSelected();
    clearPurchaseIntent();
  }

  function goSynthAfterCheckout() {
    if (checkoutSummary.value) {
      browse.selectVoice(checkoutSummary.value.catalogId);
    }
    dismissCheckout();
  }

  return {
    router,
    mySubmissions,
    pendingReview,
    myVersions,
    myVoices,
    issuedGrants,
    receivedGrants,
    myAuthorizations,
    issuedAuthorizations,
    sellerWallet,
    sellerStats,
    publishVersionId,
    publishTitle,
    publishDescription,
    publishTags,
    publishDemoText,
    publishLicenseType,
    publishPriceYuan,
    publishIncludedChars,
    publishProhibited,
    payoutAmountYuan,
    complaintText,
    grantVoiceId,
    granteeUserId,
    checkoutSummary,
    publishEligibility,
    inviteCode,
    waitlistContact,
    waitlistNote,
    activeModal,
    ownedVersions,
    isAdmin,
    openModal,
    closeModal,
    reload,
    onPublish,
    onRequestPayout,
    onPurchaseSelected,
    onDownloadDemoSelected,
    onDownloadPackSelected,
    onExportCertificate,
    verifyUrl,
    onSubmitComplaint,
    toggleProhibited,
    onGrant,
    onRevokeGrant,
    onApprove,
    onReject,
    onRegenerateDemo,
    onRedeemInvite,
    onJoinWaitlist,
    dismissCheckout,
    goSynthAfterCheckout,
    maybeAutoPurchase,
    versionOptionLabel,
    DEV_USER_PRESETS,
    PROHIBITED_DOMAIN_OPTIONS,
  };
}
