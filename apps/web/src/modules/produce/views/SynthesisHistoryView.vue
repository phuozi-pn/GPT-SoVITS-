<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  fetchSynthesisDetail,
  fetchSynthesisHistory,
  type SynthesisHistoryDetail,
  type SynthesisHistoryItem,
} from "@/api/history";
import { exportDownloadUrl } from "@/api/client";
import AppModal from "@/components/AppModal.vue";
import ErrorBanner from "@/components/ErrorBanner.vue";
import HistoryCard from "@/components/HistoryCard.vue";
import PageActionBar from "@/components/PageActionBar.vue";
import PageHero from "@/components/PageHero.vue";
import PageSurface from "@/components/PageSurface.vue";
import OscilloscopeDisplay from "@/modules/voice/components/studio/OscilloscopeDisplay.vue";
import { getPageMeta } from "@/config/navigation";
import { formatApiError } from "@/utils/apiErrors";
import { formatTokenVolumeWithUnit } from "@/utils/quotaDisplay";

const pageMeta = getPageMeta("/history", "history");

const loading = ref(false);
const detailLoading = ref(false);
const error = ref("");
const items = ref<SynthesisHistoryItem[]>([]);
const detailOpen = ref(false);
const detail = ref<SynthesisHistoryDetail | null>(null);

function formatTime(iso: string) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function statusLabel(status: string) {
  if (status === "succeeded") return "已完成";
  if (status === "failed") return "失败";
  if (status === "running") return "合成中";
  if (status === "queued") return "排队中";
  return status;
}

function itemTitle(item: SynthesisHistoryItem) {
  const name = item.voice_name ?? "未知音色";
  const label = item.voice_version_label?.trim();
  return label ? `${name} · ${label}` : name;
}

async function reload() {
  loading.value = true;
  error.value = "";
  try {
    items.value = await fetchSynthesisHistory(100);
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
}

async function openDetail(item: SynthesisHistoryItem) {
  detailOpen.value = true;
  detailLoading.value = true;
  detail.value = null;
  try {
    detail.value = await fetchSynthesisDetail(item.job_id);
  } catch (e) {
    error.value = formatApiError(e);
    detailOpen.value = false;
  } finally {
    detailLoading.value = false;
  }
}

function closeDetail() {
  detailOpen.value = false;
  detail.value = null;
}

onMounted(reload);
</script>

<template>
  <div class="page page--full history-page">
    <ErrorBanner v-if="error" :message="error" retry :loading="loading" @retry="reload" @dismiss="error = ''" />

    <PageSurface>
      <PageHero compact flow :title="pageMeta.label" :hint="pageMeta.desc">
        <template #stats>
          <p class="page-metrics">
            共 <strong>{{ items.length }}</strong> 条合成记录
          </p>
        </template>
        <template #actions>
          <button type="button" class="text-action" :disabled="loading" @click="reload">刷新</button>
        </template>
      </PageHero>

      <p v-if="loading && !items.length" class="hint history-loading" role="status">加载中…</p>
      <p v-else-if="!items.length" class="hint history-empty">暂无合成历史，去智能配音生成第一条吧。</p>

      <div v-else class="history-grid">
        <div v-for="item in items" :key="item.job_id" class="history-grid__item">
          <HistoryCard
            :title="itemTitle(item)"
            :subtitle="statusLabel(item.status)"
            :text-preview="item.text_preview"
            :audio-url="item.audio_url ?? undefined"
            :created-at="formatTime(item.created_at)"
            @select="openDetail(item)"
          />
        </div>
      </div>

      <PageActionBar label="相关">
        <router-link to="/library" class="page-action-link">智能配音</router-link>
        <router-link to="/account" class="page-action-link">账户与 Token</router-link>
        <router-link to="/projects" class="page-action-link">短剧批量</router-link>
      </PageActionBar>
    </PageSurface>

    <AppModal
      :open="detailOpen"
      label="合成详情"
      :title="detail ? itemTitle(detail) : '合成详情'"
      wide
      @close="closeDetail"
    >
      <p v-if="detailLoading" class="hint">加载详情…</p>
      <template v-else-if="detail">
        <div class="detail-meta">
          <span>{{ formatTime(detail.created_at) }}</span>
          <span>{{ statusLabel(detail.status) }}</span>
          <span v-if="detail.chars_billed">计费 {{ formatTokenVolumeWithUnit(detail.chars_billed) }}</span>
          <span v-if="detail.duration_sec">{{ detail.duration_sec.toFixed(1) }} 秒</span>
        </div>

        <div v-if="detail.audio_url" class="detail-audio">
          <OscilloscopeDisplay :src="detail.audio_url" :height="48" />
          <audio :src="detail.audio_url" controls class="detail-audio__player" />
        </div>
        <p v-else class="hint">暂无音频（任务未完成或已过期）</p>

        <div v-if="detail.segments.length > 1" class="detail-segments">
          <h3 class="detail-segments__title">分段台本</h3>
          <article v-for="(seg, idx) in detail.segments" :key="idx" class="detail-segment">
            <header class="detail-segment__head">
              <span>#{{ idx + 1 }}</span>
              <span v-if="seg.voice_name">{{ seg.voice_name }}</span>
              <span v-if="seg.role" class="detail-segment__role">{{ seg.role }}</span>
            </header>
            <p class="detail-segment__text">{{ seg.text }}</p>
          </article>
        </div>
        <div v-else class="detail-text">
          <h3 class="detail-text__title">台本内容</h3>
          <pre class="detail-text__body">{{ detail.full_text }}</pre>
        </div>

        <p v-if="detail.error_message" class="detail-error">{{ detail.error_message }}</p>
      </template>

      <template v-if="detail && detail.status === 'succeeded'" #footer>
        <a
          v-if="detail.audio_url"
          :href="exportDownloadUrl(detail.job_id)"
          class="btn btn--ghost btn--sm"
          target="_blank"
          rel="noopener"
        >
          合规导出
        </a>
        <button type="button" class="btn btn--primary btn--sm" @click="closeDetail">关闭</button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.history-page {
  gap: 12px;
}

.history-loading,
.history-empty {
  text-align: center;
  padding: 32px 0;
}

.history-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
}

.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--color-ink-muted);
}

.detail-audio {
  display: grid;
  gap: 10px;
  margin-bottom: 16px;
}

.detail-audio__player {
  width: 100%;
}

.detail-text__title,
.detail-segments__title {
  margin: 0 0 8px;
  font-size: 14px;
}

.detail-text__body {
  margin: 0;
  padding: 12px;
  border-radius: var(--radius-ui);
  background: var(--bg-surface-muted);
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
  max-height: 320px;
  overflow: auto;
}

.detail-segments {
  display: grid;
  gap: 10px;
}

.detail-segment {
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-ui);
  background: var(--bg-surface-muted);
}

.detail-segment__head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--color-ink-muted);
}

.detail-segment__role {
  color: var(--color-vu-amber);
}

.detail-segment__text {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.55;
  font-size: 14px;
}

.detail-error {
  margin-top: 12px;
  color: var(--color-danger, #c45c4a);
  font-size: 13px;
}
</style>
