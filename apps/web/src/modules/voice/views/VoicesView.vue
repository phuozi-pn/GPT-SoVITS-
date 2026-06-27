<script setup lang="ts">
import { computed, onActivated, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import AppModal from "@/components/AppModal.vue";
import ConfirmModal from "@/components/ConfirmModal.vue";
import EmptyGuide from "@/components/EmptyGuide.vue";
import ErrorBanner from "@/components/ErrorBanner.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import PageHero from "@/components/PageHero.vue";
import PageSurface from "@/components/PageSurface.vue";
import VoiceCloneCompare from "@/components/VoiceCloneCompare.vue";
import VoiceCoverPlay from "@/components/VoiceCoverPlay.vue";
import VoicePreviewButton from "@/components/VoicePreviewButton.vue";
import RackPanel from "@/modules/voice/components/studio/RackPanel.vue";
import {
  catalogStatusLabel,
  consentStatusLabel,
  deleteVoice,
  deleteVoiceVersion,
  fetchMyVoicesDetail,
  formatDuration,
  qcStatusLabel,
  unpublishCatalogEntry,
  updateVoiceName,
  updateVoiceVersion,
  versionDisplayName,
  type VoiceManageSummary,
  type VoiceVersionManageSummary,
} from "@/api/voices";
import { fetchMyCatalogSubmissions, type CatalogEntry } from "@/api/catalog";
import { useToast } from "@/composables/useToast";
import { formatApiError } from "@/utils/apiErrors";

const router = useRouter();
const { toastOk, toastError } = useToast();
const loading = ref(false);
const error = ref("");
const voices = ref<VoiceManageSummary[]>([]);
const catalogEntries = ref<CatalogEntry[]>([]);

const catalogById = computed(() => new Map(catalogEntries.value.map((e) => [e.catalog_id, e])));

const totalVersions = computed(() =>
  voices.value.reduce((n, v) => n + (v.versions?.length ?? v.version_count), 0),
);

const showRename = ref(false);
const renameVoiceId = ref("");
const renameValue = ref("");

const showEditVersion = ref(false);
const editVersion = ref<VoiceVersionManageSummary | null>(null);
const editLabel = ref("");
const editRefText = ref("");

const expandedVoiceIds = ref<Set<string>>(new Set());

// 确认对话框状态
const showDeleteVersion = ref(false);
const deleteVersionTarget = ref<VoiceVersionManageSummary | null>(null);
const showUnpublish = ref(false);
const unpublishTarget = ref<VoiceVersionManageSummary | null>(null);
const showDeleteVoice = ref(false);
const deleteVoiceTarget = ref<VoiceManageSummary | null>(null);

function toggleVoiceDetail(voiceId: string) {
  const next = new Set(expandedVoiceIds.value);
  if (next.has(voiceId)) next.delete(voiceId);
  else next.add(voiceId);
  expandedVoiceIds.value = next;
}

function isExpanded(voiceId: string) {
  return expandedVoiceIds.value.has(voiceId);
}

async function reload() {
  loading.value = true;
  error.value = "";
  try {
    const [voiceList, submissions] = await Promise.all([
      fetchMyVoicesDetail(),
      fetchMyCatalogSubmissions().catch(() => [] as CatalogEntry[]),
    ]);
    voices.value = voiceList;
    catalogEntries.value = submissions;
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
}

function openRename(voice: VoiceManageSummary) {
  renameVoiceId.value = voice.voice_id;
  renameValue.value = voice.name;
  showRename.value = true;
}

async function onRename() {
  if (!renameVoiceId.value || !renameValue.value.trim()) return;
  loading.value = true;
  error.value = "";
  try {
    await updateVoiceName(renameVoiceId.value, renameValue.value.trim());
    toastOk("音色名称已更新");
    showRename.value = false;
    await reload();
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
}

function openEditVersion(v: VoiceVersionManageSummary) {
  editVersion.value = v;
  editLabel.value = v.label ?? "";
  editRefText.value = v.ref_text ?? "";
  showEditVersion.value = true;
}

async function onSaveVersion() {
  if (!editVersion.value) return;
  loading.value = true;
  error.value = "";
  try {
    await updateVoiceVersion(editVersion.value.voice_version_id, {
      label: editLabel.value.trim() || undefined,
      ref_text: editRefText.value.trim() || undefined,
    });
    toastOk("版本资料已更新");
    showEditVersion.value = false;
    await reload();
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
}

async function onDeleteVersion(v: VoiceVersionManageSummary) {
  if (!v.can_delete) return;
  deleteVersionTarget.value = v;
  showDeleteVersion.value = true;
}

async function doDeleteVersion() {
  const v = deleteVersionTarget.value;
  if (!v) return;
  showDeleteVersion.value = false;
  loading.value = true;
  error.value = "";
  try {
    await deleteVoiceVersion(v.voice_version_id);
    toastOk("版本已删除");
    await reload();
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
}

async function onUnpublish(ver: VoiceVersionManageSummary) {
  if (!ver.catalog_id) return;
  unpublishTarget.value = ver;
  showUnpublish.value = true;
}

async function doUnpublish() {
  const ver = unpublishTarget.value;
  if (!ver?.catalog_id) return;
  showUnpublish.value = false;
  loading.value = true;
  error.value = "";
  try {
    await unpublishCatalogEntry(ver.catalog_id);
    toastOk(
      ver.catalog_status === "published"
        ? "已下架，买家授权已撤销，现在可以删除该版本"
        : "已撤回审核/下架，现在可以删除该版本",
    );
    await reload();
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
}

async function onDeleteVoice(voice: VoiceManageSummary) {
  deleteVoiceTarget.value = voice;
  showDeleteVoice.value = true;
}

async function doDeleteVoice() {
  const voice = deleteVoiceTarget.value;
  if (!voice) return;
  showDeleteVoice.value = false;
  loading.value = true;
  error.value = "";
  try {
    await deleteVoice(voice.voice_id);
    toastOk("音色已删除");
    await reload();
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
}

function goSynth(versionId: string) {
  router.push({ path: "/library", query: { voice: versionId } });
}

function goQuality(versionId: string) {
  router.push(`/quality/${versionId}`);
}

function goStudio() {
  router.push("/studio");
}

function formatDate(iso?: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function latestCloneDemoUrl(voice: VoiceManageSummary) {
  const ver = voice.versions?.[0];
  return ver?.clone_demo_audio_url ?? ver?.preview_audio_url ?? null;
}

function versionCatalogEntry(ver: VoiceVersionManageSummary, fallbackTitle: string) {
  const catalog = ver.catalog_id ? catalogById.value.get(ver.catalog_id) : undefined;
  const base = catalog
    ? {
        catalog_id: catalog.catalog_id,
        title: catalog.title,
        cover_image_url: catalog.cover_image_url,
        tags: catalog.tags ?? [],
      }
    : {
        catalog_id: ver.catalog_id ?? ver.voice_version_id,
        title: ver.catalog_title ?? fallbackTitle,
        cover_image_url: ver.catalog_cover_image_url ?? null,
        tags: ver.catalog_tags ?? [],
      };
  return base;
}

function voiceCatalogEntry(voice: VoiceManageSummary) {
  const ver = voice.versions?.find((v) => v.catalog_id) ?? voice.versions?.[0];
  if (!ver) {
    return {
      catalog_id: voice.voice_id,
      title: voice.name,
      cover_image_url: null as string | null,
      tags: [] as string[],
    };
  }
  return versionCatalogEntry(ver, voice.name);
}

function goEditCatalog(catalogId: string) {
  void router.push({ path: "/catalog", query: { pick: catalogId } });
}

onMounted(() => {
  void reload();
});

onActivated(() => {
  void reload();
});
</script>

<template>
  <div class="page page--full voices-page">
    <ErrorBanner
      v-if="error"
      :message="error"
      retry
      :loading="loading"
      @retry="reload"
      @dismiss="error = ''"
    />

    <PageSurface>
      <PageHero
        compact
        flow
        hint="每个版本可并排试听：训练前原声与克隆合成样例。"
      >
        <template #stats>
          <p class="page-metrics">
            音色 <strong>{{ voices.length }}</strong>
            · 版本 <strong>{{ totalVersions }}</strong>
          </p>
        </template>
        <template #actions>
          <button type="button" class="btn btn--primary btn--sm" @click="goStudio">训练新音色</button>
        </template>
      </PageHero>

      <RackPanel label="资产" title="我的音色与版本">
        <LoadingSpinner v-if="loading && !voices.length" inline text="正在获取音色列表…" />

        <div v-else-if="!voices.length" class="voices-empty-wrap">
          <EmptyGuide
            compact
            title="还没有自有音色"
            desc="创建音色、上传授权干声并完成训练后，即可在智能配音中使用。"
          >
            <template #actions>
              <button type="button" class="btn btn--primary btn--sm" @click="goStudio">训练新音色</button>
              <router-link to="/library" class="btn btn--sm">去智能配音导入</router-link>
            </template>
          </EmptyGuide>
        </div>

        <div v-else class="voices-list">
          <section v-for="voice in voices" :key="voice.voice_id" class="voice-group">
            <header class="voice-group__head">
              <VoiceCoverPlay
                :entry="voiceCatalogEntry(voice)"
                :src="latestCloneDemoUrl(voice)"
                size="lg"
              />
              <div class="voice-group__lead">
                <h3 class="voice-group__title">{{ voice.name }}</h3>
                <p class="hint voice-group__meta">{{ voice.version_count }} 个版本 · {{ formatDate(voice.versions?.[0]?.created_at) }}</p>
                <button
                  type="button"
                  class="voice-disclosure"
                  :aria-expanded="isExpanded(voice.voice_id)"
                  @click="toggleVoiceDetail(voice.voice_id)"
                >
                  <span class="voice-disclosure__chev" :class="{ 'voice-disclosure__chev--open': isExpanded(voice.voice_id) }" aria-hidden="true" />
                  {{ isExpanded(voice.voice_id) ? "收起训练素材与授权" : "查看训练素材与授权" }}
                </button>
              </div>
              <div class="row-actions">
                <button type="button" class="text-action" @click="openRename(voice)">重命名</button>
                <template v-if="!voice.version_count">
                  <span class="row-actions__sep" aria-hidden="true">·</span>
                  <button type="button" class="text-action text-action--danger" @click="onDeleteVoice(voice)">删除音色</button>
                </template>
              </div>
            </header>

            <ul v-if="voice.versions?.length" class="version-rows">
              <li v-for="ver in voice.versions" :key="ver.voice_version_id" class="version-row">
                <header class="version-row__header">
                  <div class="version-row__heading">
                    <strong class="version-row__name">{{ versionDisplayName(ver) }}</strong>
                    <div class="version-row__tags">
                      <span class="pill pill--muted">{{ ver.model_tag }}</span>
                      <span v-if="ver.catalog_status" class="pill pill--warn">
                        {{ catalogStatusLabel(ver.catalog_status) }}
                        <template v-if="ver.catalog_title"> · {{ ver.catalog_title }}</template>
                      </span>
                    </div>
                  </div>
                  <button type="button" class="btn btn--ghost btn--sm version-row__synth-btn" @click="goSynth(ver.voice_version_id)">
                    去合成
                  </button>
                </header>

                <VoiceCloneCompare
                  class="version-row__compare"
                  :source-audio-url="ver.source_audio_url"
                  :clone-demo-audio-url="ver.clone_demo_audio_url"
                  :show-heading="false"
                />

                <div class="version-row__footer">
                  <p v-if="!ver.clone_demo_audio_url" class="version-row__note version-row__note--info">
                    尚无合成样例：在工作台步骤 ④ 试听，或点击「质量测评」自动生成。
                  </p>
                  <p v-if="ver.ref_text" class="version-row__note version-row__note--quote">{{ ver.ref_text }}</p>
                  <p v-if="!ver.can_delete && ver.delete_block_reason" class="version-row__note version-row__note--warn">
                    {{ ver.delete_block_reason }}
                  </p>
                  <div class="row-actions version-row__actions">
                    <button type="button" class="text-action" @click="openEditVersion(ver)">编辑资料</button>
                    <template v-if="ver.catalog_id">
                      <span class="row-actions__sep" aria-hidden="true">·</span>
                      <button type="button" class="text-action text-action--accent" @click="goEditCatalog(ver.catalog_id!)">
                        编辑封面与标签
                      </button>
                    </template>
                    <template v-if="!ver.imported">
                      <span class="row-actions__sep" aria-hidden="true">·</span>
                      <button type="button" class="text-action" @click="goQuality(ver.voice_version_id)">质量测评</button>
                    </template>
                    <template v-if="ver.can_unpublish && ver.catalog_id">
                      <span class="row-actions__sep" aria-hidden="true">·</span>
                      <button type="button" class="text-action text-action--danger" @click="onUnpublish(ver)">下架</button>
                    </template>
                    <template v-if="ver.can_delete">
                      <span class="row-actions__sep" aria-hidden="true">·</span>
                      <button type="button" class="text-action text-action--danger" @click="onDeleteVersion(ver)">删除</button>
                    </template>
                  </div>
                </div>
              </li>
            </ul>
            <p v-else class="hint voice-group__empty">尚无版本——请继续训练或导入权重</p>

            <div v-if="isExpanded(voice.voice_id)" class="voice-detail">
              <section class="voice-detail__section">
                <h4 class="voice-detail__title">训练素材</h4>
                <ul v-if="voice.assets?.length" class="detail-list">
                  <li v-for="asset in voice.assets" :key="asset.asset_id" class="detail-list__row detail-list__row--asset">
                    <VoicePreviewButton :src="asset.preview_audio_url" size="md" disabled-hint="不可播" />
                    <div class="detail-list__asset-meta">
                      <span class="detail-list__label">素材</span>
                      <span class="mono detail-list__value">{{ asset.asset_id.slice(0, 8) }}…</span>
                      <span class="detail-list__label">质检</span>
                      <span>{{ qcStatusLabel(asset.qc_status, asset.qc_passed) }}</span>
                      <span class="detail-list__label">时长</span>
                      <span>{{ formatDuration(asset.duration_sec) }}</span>
                      <span class="detail-list__label">状态</span>
                      <span>{{ asset.locked ? "已锁定" : "未锁定" }}</span>
                      <span class="hint detail-list__meta">
                        {{ formatDate(asset.created_at) }}
                      </span>
                    </div>
                  </li>
                </ul>
                <p v-else class="hint">还没有上传训练素材</p>
              </section>

              <section class="voice-detail__section">
                <h4 class="voice-detail__title">授权记录</h4>
                <ul v-if="voice.consents?.length" class="detail-list">
                  <li v-for="c in voice.consents" :key="c.consent_id" class="detail-list__row">
                    <span class="detail-list__label">授权</span>
                    <span class="mono detail-list__value">{{ c.consent_id.slice(0, 8) }}…</span>
                    <span class="detail-list__label">状态</span>
                    <span>{{ consentStatusLabel(c.status) }}</span>
                    <span class="hint detail-list__meta">
                      提交 {{ formatDate(c.created_at) }}
                      <template v-if="c.approved_at"> · 通过 {{ formatDate(c.approved_at) }}</template>
                    </span>
                  </li>
                </ul>
                <p v-else class="hint">还没有声纹授权记录——训练前需在工作台提交</p>
              </section>
            </div>
          </section>
        </div>
      </RackPanel>
    </PageSurface>

    <AppModal :open="showRename" label="重命名" title="修改音色名称" @close="showRename = false">
      <label class="field">
        <span>音色名称</span>
        <input v-model="renameValue" maxlength="128" />
      </label>
      <template #footer>
        <button type="button" class="btn btn--ghost btn--sm" @click="showRename = false">取消</button>
        <button type="button" class="btn btn--primary btn--sm" :disabled="loading" @click="onRename">保存</button>
      </template>
    </AppModal>

    <AppModal :open="showEditVersion" label="版本" title="编辑版本资料" @close="showEditVersion = false">
      <div class="form-stack">
        <label class="field">
          <span>展示标签</span>
          <input v-model="editLabel" maxlength="128" placeholder="如：旁白男声-正式版" />
        </label>
        <label class="field">
          <span>参考文本</span>
          <textarea v-model="editRefText" rows="3" maxlength="4000" placeholder="与参考音频一致的文本" />
        </label>
      </div>
      <template #footer>
        <button type="button" class="btn btn--ghost btn--sm" @click="showEditVersion = false">取消</button>
        <button type="button" class="btn btn--primary btn--sm" :disabled="loading" @click="onSaveVersion">保存</button>
      </template>
    </AppModal>

    <!-- 确认对话框 -->
    <ConfirmModal
      :open="showDeleteVersion"
      title="删除版本"
      tone="danger"
      confirm-label="确认删除"
      :message="`确定删除「${deleteVersionTarget ? versionDisplayName(deleteVersionTarget) : ''}」？此操作不可恢复。`"
      @close="showDeleteVersion = false"
      @confirm="doDeleteVersion"
    />

    <ConfirmModal
      :open="showUnpublish"
      title="下架音色版本"
      tone="warn"
      confirm-label="确认下架"
      :message="unpublishTarget
        ? `确定下架「${unpublishTarget.catalog_title || versionDisplayName(unpublishTarget)}」？`
          + `当前状态：${unpublishTarget.catalog_status === 'published' ? '已上架' : '审核中'}`
          + (unpublishTarget.catalog_status === 'published' ? '，已购用户的授权将被撤销。' : '。')
        : ''"
      @close="showUnpublish = false"
      @confirm="doUnpublish"
    />

    <ConfirmModal
      :open="showDeleteVoice"
      title="删除音色"
      tone="danger"
      confirm-label="确认删除"
      :message="`确定删除音色「${deleteVoiceTarget?.name ?? ''}」及其全部可删版本？`"
      @close="showDeleteVoice = false"
      @confirm="doDeleteVoice"
    />
  </div>
</template>

<style scoped>
.voices-page {
  gap: 12px;
}

.voices-empty-wrap {
  padding-top: 8px;
}

/* ── 音色列表容器 ─────────────────────────── */
.voices-list {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* ── 每个音色分组 ─────────────────────────── */
.voice-group__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 16px;
  margin-bottom: 16px;
}

.voice-group__head > .voice-cover-play {
  margin-top: 2px;
}

.detail-list__row--asset {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.detail-list__asset-meta {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 3px 10px;
}

.voice-group__lead {
  min-width: 0;
  flex: 1;
}

.voice-group__title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  line-height: 1.3;
}

.voice-group__meta {
  margin: 6px 0 0;
  font-size: 13px;
}

.voice-disclosure {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 0;
  border: none;
  background: none;
  font-size: 13px;
  color: var(--color-ink-muted);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
  transition: color var(--duration-fast);
}

.voice-disclosure:hover {
  color: var(--color-ink);
}

.voice-disclosure__chev {
  display: inline-block;
  width: 0.45em;
  height: 0.45em;
  border-right: 1.5px solid currentColor;
  border-bottom: 1.5px solid currentColor;
  transform: rotate(-45deg) translateY(-1px);
  transition: transform var(--duration-fast) var(--ease-out);
}

.voice-disclosure__chev--open {
  transform: rotate(45deg) translateY(-2px);
}

.voice-group + .voice-group {
  padding-top: 32px;
  border-top: 1px solid rgb(255 255 255 / 0.08);
}

.voice-group__empty {
  margin: 8px 0 0;
  padding: 18px 20px;
  border: 1px dashed rgb(255 255 255 / 0.06);
  border-radius: var(--radius-ui);
  font-size: 13px;
  text-align: center;
}

/* ── 版本行列表 ───────────────────────────── */
.version-rows {
  list-style: none;
  margin: 4px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.version-row {
  display: grid;
  gap: 0;
  overflow: hidden;
  border: 1px solid var(--border-glow);
  border-radius: calc(var(--radius-ui) + 4px);
  background: var(--bg-surface-glass);
  box-shadow: var(--shadow-soft);
  transition:
    border-color var(--duration-fast),
    box-shadow var(--duration-fast);
}

.version-row:hover {
  border-color: rgb(255 255 255 / 0.14);
  box-shadow: 0 6px 24px rgb(0 0 0 / 0.14);
}

.version-row__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px 16px;
  padding: 16px 18px 14px;
  border-bottom: 1px solid rgb(255 255 255 / 0.06);
}

.version-row__heading {
  display: grid;
  gap: 8px;
  min-width: 0;
}

.version-row__name {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.3;
}

.version-row__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.version-row__synth-btn {
  flex-shrink: 0;
  margin-top: 2px;
}

.version-row__compare {
  margin: 0;
  border: none;
  border-radius: 0;
  border-bottom: 1px solid rgb(255 255 255 / 0.06);
  background: transparent;
  box-shadow: none;
}

.version-row__footer {
  display: grid;
  gap: 10px;
  padding: 14px 18px 16px;
}

.version-row__note {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
}

.version-row__note--info {
  padding: 10px 12px;
  border-radius: var(--radius-ui);
  border: 1px dashed rgb(255 255 255 / 0.1);
  background: var(--bg-surface-muted);
  color: var(--color-ink-muted);
}

.version-row__note--quote {
  padding-left: 12px;
  border-left: 2px solid var(--border-glow);
  color: var(--color-ink-muted);
}

.version-row__note--warn {
  color: var(--color-danger, #c45c4a);
}

.version-row__actions {
  margin-top: 2px;
}

@media (max-width: 720px) {
  .version-row__header {
    flex-direction: column;
    align-items: stretch;
  }

  .version-row__synth-btn {
    align-self: flex-start;
  }
}

.pill--muted {
  color: var(--color-ink-muted);
  border-color: var(--border-glow);
  background: var(--bg-surface-muted);
}

/* ── 展开：训练素材 + 授权记录 ──────────────── */
.voice-detail {
  margin-top: 18px;
  padding: 20px 22px;
  border: 1px solid var(--border-glow);
  border-radius: var(--radius-ui);
  background: var(--bg-surface-glass);
  display: grid;
  gap: 22px;
}

.voice-detail__section {
  min-width: 0;
}

.voice-detail__title {
  margin: 0 0 12px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-brushed-dark);
}

.detail-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-list__row {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 3px 10px;
  padding: 10px 14px;
  border-radius: var(--radius-ui);
  background: var(--bg-surface-muted);
  font-size: 13px;
}

.detail-list__label {
  color: var(--color-brushed-dark);
  font-size: 12px;
  white-space: nowrap;
}

.detail-list__label::after {
  content: "：";
}

.detail-list__value {
  font-size: 13px;
  word-break: break-all;
}

.detail-list__meta {
  grid-column: 1 / -1;
  margin-top: 2px;
  font-size: 12px;
}

/* ── 响应式：小屏调整 ──────────────────────── */
@media (max-width: 720px) {
  .voice-group__head {
    flex-direction: column;
    gap: 8px;
  }

  .voice-group + .voice-group {
    padding-top: 24px;
  }

  .version-row {
    padding: 14px 16px;
  }

  .voice-detail {
    padding: 16px 18px;
    gap: 18px;
  }

  .detail-list__row {
    padding: 8px 10px;
    font-size: 12px;
  }
}
</style>
