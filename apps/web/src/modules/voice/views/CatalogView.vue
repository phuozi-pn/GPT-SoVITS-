<script setup lang="ts">
import { onMounted } from "vue";
import { formatPriceCents, getDevUserId } from "@/api/catalog";
import CatalogCoverEditor from "@/modules/voice/components/CatalogCoverEditor.vue";
import CatalogModals from "@/modules/voice/components/CatalogModals.vue";
import CatalogVoiceGrid from "@/modules/voice/components/CatalogVoiceGrid.vue";
import MakeWorkspace from "@/modules/produce/components/MakeWorkspace.vue";
import DetailStrip from "@/components/DetailStrip.vue";
import DetailStripItem from "@/components/DetailStripItem.vue";
import VoiceCatalogMeta from "@/components/VoiceCatalogMeta.vue";
import PageActionBar from "@/components/PageActionBar.vue";
import PageActionLink from "@/components/PageActionLink.vue";
import PageHero from "@/components/PageHero.vue";
import PageSurface from "@/components/PageSurface.vue";
import RackPanel from "@/modules/voice/components/studio/RackPanel.vue";
import { useCatalogBrowse, useCatalogVoicesForEntry } from "@/modules/voice/composables/useCatalogBrowse";
import { useCatalogManage } from "@/modules/voice/composables/useCatalogManage";
import { useCatalogSynth } from "@/modules/voice/composables/useCatalogSynth";
import { isLabsEnabled } from "@/config/features";
import { catalogAccessPillClass, catalogAccessStatus, catalogOwnerLabel, licenseLabel } from "@/utils/catalogDisplay";

const browse = useCatalogBrowse();
const manage = useCatalogManage(browse);
const synth = useCatalogSynth(browse.selectedEntry, browse.error, browse.success);
const catalogVoices = useCatalogVoicesForEntry(browse.selectedEntry);

onMounted(async () => {
  await browse.initFromRoute();
  await manage.reload();
  await maybeAutoPurchase();
});

const {
  entries,
  availableTags,
  selectedTags,
  tagQuery,
  selectedCatalogId,
  viewMode,
  loading,
  error,
  success,
  featuredList,
  heroEntries,
  gridEntries,
  showAllGrid,
  selectedEntry,
  applyTagQuery,
  clearTagFilter,
  toggleTag,
  selectVoice,
  contactCreator,
  goLibrary,
  loadCatalog,
} = browse;

const {
  mySubmissions,
  pendingReview,
  myAuthorizations,
  issuedAuthorizations,
  sellerWallet,
  sellerStats,
  myVoices,
  issuedGrants,
  receivedGrants,
  publishVersionId,
  publishTitle,
  publishDescription,
  publishTags,
  publishCoverUrl,
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
  onPublish,
  onRequestPayout,
  onPurchaseSelected,
  onDownloadDemoSelected,
  onDownloadPackSelected,
  onExportCertificate,
  onSubmitComplaint,
  toggleProhibited,
  onGrant,
  onRevokeGrant,
  onApprove,
  onReject,
  onRegenerateDemo,
  openEditEntry,
  openEditEntryById,
  onSaveEditEntry,
  onEntryCoverUpdated,
  editingEntry,
  editTitle,
  editTags,
  editCoverUrl,
  onRedeemInvite,
  onJoinWaitlist,
  dismissCheckout,
  goSynthAfterCheckout,
  maybeAutoPurchase,
  versionOptionLabel,
  DEV_USER_PRESETS,
  PROHIBITED_DOMAIN_OPTIONS,
  router: manageRouter,
} = manage;

const {
  segments,
  multiMode,
  catalogVoiceId,
  speed,
  temperature,
  synthBusy,
  aiAck,
  catalogAudioUrl,
  catalogExportJobId,
  exportDownloadUrl,
  onCatalogSynth,
} = synth;
</script>

<template>
  <div class="page page--full page--fill catalog-page">
    <div v-if="error" class="alert alert--error">{{ error }}</div>
    <div v-if="success" class="alert alert--ok">{{ success }}</div>

    <PageSurface>
      <PageHero compact flow title="音色馆">
        <template #stats>
          <p class="page-metrics">
            精选 <strong>{{ featuredList.length }}</strong>
            · 公开 <strong>{{ entries.length }}</strong>
            <template v-if="selectedEntry"> · 试听 <strong>{{ selectedEntry.title }}</strong></template>
          </p>
        </template>
      </PageHero>

      <RackPanel label="音色馆" title="精选公开音色" body-class="catalog-rack-body">
        <template #actions>
          <div class="catalog-view-tabs">
            <button
              type="button"
              class="catalog-view-tab"
              :class="{ 'catalog-view-tab--on': viewMode === 'featured' }"
              @click="viewMode = 'featured'"
            >
              精选
            </button>
            <button
              type="button"
              class="catalog-view-tab"
              :class="{ 'catalog-view-tab--on': viewMode === 'all' }"
              @click="viewMode = 'all'"
            >
              全部
            </button>
          </div>
        </template>

        <div class="catalog-layout">
          <div class="catalog-layout__main">
            <CatalogVoiceGrid
              :entries="entries"
              :hero-entries="heroEntries"
              :grid-entries="gridEntries"
              :show-all-grid="showAllGrid"
              :selected-tags="selectedTags"
              :selected-catalog-id="selectedCatalogId"
              :available-tags="availableTags"
              :tag-query="tagQuery"
              :loading="loading"
              @update:tag-query="tagQuery = $event"
              @apply-tag-query="applyTagQuery"
              @clear-tag-filter="clearTagFilter"
              @toggle-tag="toggleTag"
              @select-voice="selectVoice"
              @load-catalog="loadCatalog"
              @contact-creator="contactCreator"
              @edit-entry="openEditEntryById"
            />
          </div>

          <div class="catalog-layout__aside">
            <section
              v-if="selectedEntry && selectedEntry.owner_user_id === getDevUserId()"
              class="catalog-aside-publish"
            >
              <div class="catalog-aside-publish__head">
                <h3 class="catalog-aside-publish__title">我的发布设置</h3>
                <button type="button" class="text-action" @click="openEditEntry(selectedEntry)">
                  编辑标签
                </button>
              </div>
              <CatalogCoverEditor
                :title="selectedEntry.title"
                :tags="selectedEntry.tags"
                :catalog-id="selectedEntry.catalog_id"
                :disabled="loading"
                :cover-url="selectedEntry.cover_image_url ?? ''"
                @entry-updated="onEntryCoverUpdated"
              />
            </section>

            <DetailStrip v-if="selectedEntry" class="catalog-aside-strip">
              <DetailStripItem label="展示名">{{ selectedEntry.title }}</DetailStripItem>
              <DetailStripItem label="创作者">
                <router-link class="text-action" :to="`/creator/${selectedEntry.owner_user_id}`">
                  {{ catalogOwnerLabel(selectedEntry) }}
                </router-link>
              </DetailStripItem>
              <DetailStripItem label="引擎音色">{{ selectedEntry.voice_name }}</DetailStripItem>
              <DetailStripItem label="授权">{{ licenseLabel(selectedEntry.license_type) }}</DetailStripItem>
              <DetailStripItem label="价格">{{ formatPriceCents(selectedEntry.price_cents) }}</DetailStripItem>
              <DetailStripItem v-if="selectedEntry.price_cents > 0" label="含字符">
                {{ selectedEntry.included_chars.toLocaleString() }} 字
              </DetailStripItem>
              <DetailStripItem label="状态">
                <span
                  :class="catalogAccessPillClass(catalogAccessStatus(selectedEntry, getDevUserId()).tone)"
                >
                  {{ catalogAccessStatus(selectedEntry, getDevUserId()).label }}
                </span>
              </DetailStripItem>
            </DetailStrip>

            <div v-if="selectedEntry?.tags.length" class="catalog-aside-tags">
              <VoiceCatalogMeta :entry="selectedEntry" :show-author="false" prominent :tag-limit="10" />
            </div>

            <MakeWorkspace
              v-if="selectedEntry"
              v-model:segments="segments"
              v-model:multi-mode="multiMode"
              v-model:voice-id="catalogVoiceId"
              v-model:ai-ack="aiAck"
              v-model:speed="speed"
              v-model:temperature="temperature"
              variant="studio"
              class="catalog-make"
              :voices="catalogVoices"
              :voice-title="selectedEntry.title"
              :voice-subtitle="selectedEntry.voice_name"
              :busy="synthBusy"
              :audio-url="catalogAudioUrl"
              :export-href="catalogExportJobId ? exportDownloadUrl(catalogExportJobId) : undefined"
              generate-label="试听合成"
              @generate="onCatalogSynth"
            />
            <p v-else class="hint catalog-aside-empty">点击左侧精选音色卡片，在此输入台词试听合成</p>

            <div v-if="selectedEntry" class="catalog-aside-actions row-actions">
              <button
                v-if="
                  selectedEntry.price_cents > 0 &&
                  !selectedEntry.purchased &&
                  selectedEntry.owner_user_id !== getDevUserId()
                "
                class="btn btn--primary btn--sm"
                @click="onPurchaseSelected"
              >
                购买授权 {{ formatPriceCents(selectedEntry.price_cents) }}
              </button>
              <p
                v-else-if="selectedEntry.owner_user_id === getDevUserId() && selectedEntry.price_cents > 0"
                class="hint catalog-aside-hint"
              >
                你是创作者，买家需用其他账号购买
              </p>
              <button class="text-action" @click="onDownloadDemoSelected">下载样音</button>
              <span class="row-actions__sep" aria-hidden="true">·</span>
              <button
                v-if="selectedEntry.can_use || selectedEntry.price_cents === 0"
                class="text-action"
                @click="onDownloadPackSelected"
              >
                下载音色包
              </button>
              <template v-if="selectedEntry.owner_user_id !== getDevUserId()">
                <span class="row-actions__sep" aria-hidden="true">·</span>
                <button
                  class="text-action text-action--accent"
                  @click="contactCreator(selectedEntry.owner_user_id, selectedEntry.title)"
                >
                  联系创作者
                </button>
              </template>
              <span class="row-actions__sep" aria-hidden="true">·</span>
              <button class="text-action" @click="goLibrary(selectedEntry.voice_version_id)">音色库详情</button>
              <template v-if="isAdmin">
                <span class="row-actions__sep" aria-hidden="true">·</span>
                <button class="text-action" @click="onRegenerateDemo(selectedEntry.catalog_id)">
                  重生成样音
                </button>
              </template>
            </div>
          </div>
        </div>
      </RackPanel>

      <PageActionBar label="创作者与交易">
        <PageActionLink @click="openModal('publish')">发布音色</PageActionLink>
        <PageActionLink
          v-if="mySubmissions.length"
          :badge="mySubmissions.length"
          @click="openModal('submissions')"
        >
          我的发布
        </PageActionLink>
        <PageActionLink
          v-if="isAdmin"
          :badge="pendingReview.length || undefined"
          @click="openModal('review')"
        >
          审核队列
        </PageActionLink>
        <PageActionLink
          v-if="myAuthorizations.length"
          :badge="myAuthorizations.length"
          @click="openModal('authorizations')"
        >
          我的授权
        </PageActionLink>
        <PageActionLink v-if="sellerWallet && isLabsEnabled()" @click="openModal('wallet')">
          卖家钱包
        </PageActionLink>
        <PageActionLink
          v-if="issuedAuthorizations.length"
          :badge="issuedAuthorizations.length"
          @click="openModal('sales')"
        >
          售出授权
        </PageActionLink>
        <PageActionLink @click="openModal('complaint')">侵权投诉</PageActionLink>
        <PageActionLink @click="openModal('grant')">单独授权</PageActionLink>
      </PageActionBar>
    </PageSurface>

    <CatalogModals
      :active-modal="activeModal"
      :loading="loading"
      :selected-entry="selectedEntry"
      :owned-versions="ownedVersions"
      :my-submissions="mySubmissions"
      :pending-review="pendingReview"
      :my-authorizations="myAuthorizations"
      :issued-authorizations="issuedAuthorizations"
      :seller-wallet="sellerWallet"
      :seller-stats="sellerStats"
      :my-voices="myVoices"
      :issued-grants="issuedGrants"
      :received-grants="receivedGrants"
      :publish-version-id="publishVersionId"
      :publish-title="publishTitle"
      :publish-description="publishDescription"
      :publish-tags="publishTags"
      :publish-cover-url="publishCoverUrl"
      :publish-demo-text="publishDemoText"
      :publish-license-type="publishLicenseType"
      :publish-price-yuan="publishPriceYuan"
      :publish-included-chars="publishIncludedChars"
      :publish-prohibited="publishProhibited"
      :payout-amount-yuan="payoutAmountYuan"
      :complaint-text="complaintText"
      :grant-voice-id="grantVoiceId"
      :grantee-user-id="granteeUserId"
      :checkout-summary="checkoutSummary"
      :publish-eligibility="publishEligibility"
      :invite-code="inviteCode"
      :waitlist-contact="waitlistContact"
      :waitlist-note="waitlistNote"
      :editing-entry="editingEntry"
      :edit-title="editTitle"
      :edit-tags="editTags"
      :edit-cover-url="editCoverUrl"
      :version-option-label="versionOptionLabel"
      :dev-user-presets="DEV_USER_PRESETS"
      :prohibited-domain-options="PROHIBITED_DOMAIN_OPTIONS"
      @close="closeModal"
      @publish="onPublish"
      @request-payout="onRequestPayout"
      @submit-complaint="onSubmitComplaint"
      @grant="onGrant"
      @revoke-grant="onRevokeGrant"
      @approve="onApprove"
      @reject="onReject"
      @edit-entry="openEditEntry"
      @save-edit-entry="onSaveEditEntry"
      @entry-cover-updated="onEntryCoverUpdated"
      @redeem-invite="onRedeemInvite"
      @join-waitlist="onJoinWaitlist"
      @export-certificate="onExportCertificate"
      @toggle-prohibited="toggleProhibited"
      @dismiss-checkout="dismissCheckout"
      @go-synth-after-checkout="goSynthAfterCheckout"
      @go-library="manageRouter.push('/library')"
      @update:publish-version-id="publishVersionId = $event"
      @update:publish-title="publishTitle = $event"
      @update:publish-description="publishDescription = $event"
      @update:publish-tags="publishTags = $event"
      @update:publish-cover-url="publishCoverUrl = $event"
      @update:publish-demo-text="publishDemoText = $event"
      @update:publish-license-type="publishLicenseType = $event"
      @update:publish-price-yuan="publishPriceYuan = $event"
      @update:publish-included-chars="publishIncludedChars = $event"
      @update:payout-amount-yuan="payoutAmountYuan = $event"
      @update:complaint-text="complaintText = $event"
      @update:grant-voice-id="grantVoiceId = $event"
      @update:grantee-user-id="granteeUserId = $event"
      @update:invite-code="inviteCode = $event"
      @update:waitlist-contact="waitlistContact = $event"
      @update:waitlist-note="waitlistNote = $event"
      @update:edit-title="editTitle = $event"
      @update:edit-tags="editTags = $event"
      @update:edit-cover-url="editCoverUrl = $event"
    />
  </div>
</template>

<style scoped>
.catalog-page {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.catalog-rack-body {
  padding: 0 !important;
}

/* ── 主布局：左侧音色列表 + 右侧试听面板 ────── */
.catalog-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 380px);
  gap: 0;
  min-height: 500px;
}

/* ── 左侧：音色网格区 ──────────────────────── */
.catalog-layout__main {
  padding: clamp(18px, 2.4vw, 28px);
  min-width: 0;
  border-right: 1px solid var(--color-line);
  display: flex;
  flex-direction: column;
}

.catalog-layout__main > :first-child {
  flex: 1;
}

/* ── 右侧：详情 + 试听合成面板 ────────────── */
.catalog-layout__aside {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: clamp(18px, 2.4vw, 28px);
  background: var(--bg-surface-muted);
  min-width: 0;
  overflow-y: auto;
}

.catalog-aside-publish {
  margin-bottom: 18px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--color-line);
}

.catalog-aside-publish__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.catalog-aside-publish__title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.catalog-aside-strip {
  margin-bottom: 18px;
}

.catalog-aside-tags {
  margin-bottom: 14px;
}

.catalog-make {
  flex: 1;
  min-height: 180px;
}

.catalog-aside-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 24px;
  padding: 24px 18px;
  text-align: center;
  border: 1px dashed rgb(255 255 255 / 0.08);
  border-radius: var(--radius-ui);
}

.catalog-aside-actions {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-line);
  flex-wrap: wrap;
}

/* ── 响应式：小屏堆叠 ─────────────────────── */
@media (max-width: 960px) {
  .catalog-layout {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .catalog-layout__main {
    border-right: none;
    border-bottom: 1px solid var(--color-line);
    padding: 16px;
  }

  .catalog-layout__aside {
    padding: 16px;
  }
}
</style>
