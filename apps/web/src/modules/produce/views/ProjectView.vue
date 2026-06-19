<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  pollJob,
  exportDownloadUrl,
  getBatchLines,
  retryBatchLines,
  type JobResponse,
  type BatchLinesData,
} from "@/api/client";
import {
  bindProjectRole,
  createProject,
  fetchProjects,
  fetchVoiceVersions,
  submitBatchCsv,
  type ProjectSummary,
  type VoiceVersionSummary,
} from "@/api/library";
import { formatApiError } from "@/utils/apiErrors";
import AppModal from "@/components/AppModal.vue";
import DetailStrip from "@/components/DetailStrip.vue";
import DetailStripItem from "@/components/DetailStripItem.vue";
import ErrorBanner from "@/components/ErrorBanner.vue";
import { getPageMeta } from "@/config/navigation";
import GuidePanel from "@/components/GuidePanel.vue";
import PageActionBar from "@/components/PageActionBar.vue";
import PageActionLink from "@/components/PageActionLink.vue";
import PageHero from "@/components/PageHero.vue";
import PageSurface from "@/components/PageSurface.vue";
import RackPanel from "@/modules/voice/components/studio/RackPanel.vue";
import TapeReel from "@/modules/voice/components/studio/TapeReel.vue";

const pageMeta = getPageMeta("/projects", "projects");

const BATCH_STEPS = [
  { n: 1, title: "创建项目", desc: "为短剧或系列起名，便于管理多批次任务" },
  { n: 2, title: "绑定角色", desc: "将 CSV 中的角色名映射到已训练的音色版本" },
  { n: 3, title: "上传 CSV", desc: "每行独立合成，失败行不影响其余行" },
  { n: 4, title: "下载 ZIP", desc: "含合规说明、manifest 与带 AI 标识的音频" },
] as const;

const router = useRouter();
const projects = ref<ProjectSummary[]>([]);
const versions = ref<VoiceVersionSummary[]>([]);
const projectName = ref("短剧项目1");
const selectedProjectId = ref("");
const roleName = ref("龙宫");
const roleVoiceId = ref("");
const batchLog = ref("");
const batchJobId = ref("");
const batchSucceeded = ref<number | null>(null);
const batchFailed = ref<number | null>(null);
const batchLines = ref<BatchLinesData | null>(null);
const showLineDetails = ref(false);
const retrying = ref(false);
const error = ref("");
const busy = ref(false);
const busyLabel = ref("处理中…");

const currentProject = computed(() =>
  projects.value.find((p) => p.project_id === selectedProjectId.value),
);

const batchDone = computed(() => !!batchJobId.value && !busy.value);
const exportHref = computed(() => (batchJobId.value ? exportDownloadUrl(batchJobId.value) : ""));
const canUpload = computed(() => !!selectedProjectId.value && !busy.value);
const showCreate = ref(false);
const showBind = ref(false);

async function reload() {
  projects.value = await fetchProjects();
  versions.value = await fetchVoiceVersions();
  if (!selectedProjectId.value && projects.value.length) {
    selectedProjectId.value = projects.value[0].project_id;
  }
  if (!roleVoiceId.value && versions.value.length) {
    roleVoiceId.value = versions.value[0].voice_version_id;
  }
}

onMounted(async () => {
  try {
    await reload();
  } catch (e) {
    error.value = formatApiError(e);
  }
});

async function onCreateProject() {
  error.value = "";
  busy.value = true;
  busyLabel.value = "创建项目…";
  try {
    const p = await createProject(projectName.value.trim());
    selectedProjectId.value = p.project_id;
    showCreate.value = false;
    await reload();
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    busy.value = false;
  }
}

async function onBindRole() {
  if (!selectedProjectId.value) return;
  error.value = "";
  busy.value = true;
  busyLabel.value = "绑定角色…";
  try {
    await bindProjectRole(selectedProjectId.value, roleName.value.trim(), roleVoiceId.value);
    showBind.value = false;
    await reload();
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    busy.value = false;
  }
}

function onPollProgress(j: JobResponse) {
  const parts = [`状态 ${j.status}`];
  if (j.line_count != null) parts.push(`共 ${j.line_count} 行`);
  if (j.succeeded_count != null) parts.push(`成功 ${j.succeeded_count}`);
  if (j.failed_count != null) parts.push(`失败 ${j.failed_count}`);
  batchLog.value = parts.join(" · ");
}

async function onCsvChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file || !selectedProjectId.value) return;
  error.value = "";
  batchJobId.value = "";
  batchSucceeded.value = null;
  batchFailed.value = null;
  batchLog.value = `上传 ${file.name}…`;
  busy.value = true;
  busyLabel.value = "批量合成中…";
  try {
    const res = await submitBatchCsv(selectedProjectId.value, file);
    batchLog.value = `任务 ${res.job_id.slice(0, 8)}… · ${res.line_count} 行排队中`;
    const job = await pollJob(res.job_id, onPollProgress, 600_000);
    if (job.status !== "succeeded") {
      throw new Error(job.error_message ?? "批量失败——请确认 batch worker 是否在运行");
    }
    batchJobId.value = res.job_id;
    batchSucceeded.value = job.succeeded_count ?? null;
    batchFailed.value = job.failed_count ?? null;
    batchLog.value = `完成：成功 ${batchSucceeded.value ?? "?"} 行${
      batchFailed.value ? `，失败 ${batchFailed.value} 行` : ""
    }`;
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    busy.value = false;
    input.value = "";
  }
}

async function onLoadLines() {
  if (!batchJobId.value) return;
  try {
    batchLines.value = await getBatchLines(batchJobId.value);
    showLineDetails.value = true;
  } catch (e) {
    error.value = formatApiError(e);
  }
}

async function onRetryFailedLines() {
  if (!batchJobId.value || !batchLines.value) return;
  const failedIndices = batchLines.value.lines
    .filter((l) => l.status === "failed")
    .map((l) => l.line_index);
  if (!failedIndices.length) return;

  retrying.value = true;
  error.value = "";
  try {
    batchLines.value = await retryBatchLines(batchJobId.value, failedIndices);
    // 重新入队后重新轮询
    batchLog.value = `重试 ${failedIndices.length} 行…`;
    const job = await pollJob(batchJobId.value, onPollProgress, 600_000);
    if (job.status !== "succeeded") {
      throw new Error(job.error_message ?? "重试失败");
    }
    batchSucceeded.value = job.succeeded_count ?? null;
    batchFailed.value = job.failed_count ?? null;
    batchLog.value = `完成：成功 ${batchSucceeded.value ?? "?"} 行${
      batchFailed.value ? `，失败 ${batchFailed.value} 行` : ""
    }`;
    batchLines.value = await getBatchLines(batchJobId.value);
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    retrying.value = false;
  }
}

function goLibrary() {
  router.push("/library");
}
</script>

<template>
  <div class="page page--full project-page">
    <div v-if="busy" class="busy-overlay" aria-live="polite">
      <div class="busy-overlay__box">
        <TapeReel :spinning="true" :size="72" />
        <p class="rack-title" style="margin: 16px 0 4px">{{ busyLabel }}</p>
        <p class="hint">批量任务进行中，请勿关闭页面</p>
      </div>
    </div>

    <ErrorBanner
      v-if="error"
      :message="error"
      retry
      :loading="busy"
      @retry="reload"
      @dismiss="error = ''"
    />

    <PageSurface>
      <PageHero compact flow title="短剧批量" :hint="pageMeta.desc">
      <template #stats>
        <p class="page-metrics">
          项目 <strong>{{ projects.length }}</strong>
          <template v-if="currentProject"> · 角色 <strong>{{ currentProject.roles.length }}</strong></template>
          · 音色版本 <strong>{{ versions.length }}</strong>
          <template v-if="batchSucceeded != null"> · 上次批量 <strong>{{ batchSucceeded }} 行</strong></template>
        </p>
      </template>
      <template #actions>
        <div class="hero-actions">
          <button type="button" class="btn btn--primary btn--sm" @click="showCreate = true">新建项目</button>
          <span class="row-actions">
            <button
              type="button"
              class="text-action"
              :disabled="!selectedProjectId"
              @click="showBind = true"
            >
              绑定角色
            </button>
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <a class="text-action" href="/samples/batch_template.csv" download>CSV 模板</a>
          </span>
        </div>
      </template>
      </PageHero>

      <div class="page-split">
      <RackPanel label="批量" title="批量工作台" class="page-split__main">
        <DetailStrip v-if="currentProject" class="batch-strip">
          <DetailStripItem label="当前项目" :value="currentProject.name" />
          <DetailStripItem label="已绑角色" :value="`${currentProject.roles.length} 个`" />
          <DetailStripItem label="可用音色" :value="`${versions.length} 个版本`" />
        </DetailStrip>

        <section class="batch-section">
          <h3 class="batch-section__title">项目与角色</h3>
          <p v-if="!projects.length" class="hint batch-section__lead">
            还没有短剧项目——点击「新建项目」开始批量出片。若台词尚在编辑，可先在
            <router-link to="/library">智能配音</router-link> 用多人情景试配。
          </p>
          <label v-else class="field">
            选择项目
            <select v-model="selectedProjectId" :disabled="busy">
              <option v-for="p in projects" :key="p.project_id" :value="p.project_id">{{ p.name }}</option>
            </select>
          </label>

          <ul v-if="currentProject?.roles.length" class="grant-list">
            <li v-for="r in currentProject!.roles" :key="r.role_id">
              <span>{{ r.role_name }}</span>
              <span class="hint">{{ r.voice_version_id.slice(0, 8) }}…</span>
            </li>
          </ul>
          <p v-else-if="selectedProjectId" class="hint">还没有绑定角色——点击「绑定角色」</p>
        </section>

        <section class="batch-section">
          <h3 class="batch-section__title">CSV 批量合成</h3>
          <p class="hint batch-section__lead">
            表头 <code>role,text</code>（或 <code>角色,台词</code>），角色名须与绑定一致。
          </p>

          <label
            class="upload-zone"
            :class="{ 'upload-zone--disabled': !canUpload }"
          >
            <input
              type="file"
              accept=".csv,text/csv"
              :disabled="!canUpload"
              hidden
              @change="onCsvChange"
            />
            <p class="upload-zone__title">选择 CSV 文件</p>
            <p class="hint upload-zone__sub">
              {{ canUpload ? "点击或拖入文件，开始批量合成" : "请先创建并选择项目" }}
            </p>
          </label>

          <p v-if="batchLog" class="log-panel batch-log">{{ batchLog }}</p>
        </section>

        <section v-if="batchDone" class="batch-section batch-section--lines">
          <div class="batch-section__header">
            <h3 class="batch-section__title">逐行状态</h3>
            <button type="button" class="text-action" @click="onLoadLines">
              {{ showLineDetails ? "刷新" : "查看详情" }}
            </button>
          </div>

          <div v-if="showLineDetails && batchLines" class="line-detail-panel">
            <div class="line-summary-bar">
              <span class="line-stat line-stat--ok">成功 {{ batchLines.succeeded }}</span>
              <span class="line-stat line-stat--fail" v-if="batchLines.failed">失败 {{ batchLines.failed }}</span>
              <span class="line-stat" v-if="batchLines.running">运行中 {{ batchLines.running }}</span>
              <span class="line-stat" v-if="batchLines.queued">排队 {{ batchLines.queued }}</span>
              <button
                v-if="batchLines.failed > 0"
                type="button"
                class="btn btn--sm"
                :disabled="retrying"
                @click="onRetryFailedLines"
              >
                {{ retrying ? "重试中…" : `重试 ${batchLines.failed} 行` }}
              </button>
            </div>

            <ul class="line-list">
              <li
                v-for="l in batchLines.lines"
                :key="l.line_index"
                class="line-row"
                :class="`line-row--${l.status}`"
              >
                <span class="line-row__idx">{{ l.line_index }}</span>
                <span class="line-row__role">{{ l.role }}</span>
                <span class="line-row__text">{{ l.text.slice(0, 40) }}{{ l.text.length > 40 ? '…' : '' }}</span>
                <span class="line-row__status">
                  <template v-if="l.status === 'succeeded'">
                    <span class="status-dot status-dot--ok"></span>
                    {{ l.duration_sec?.toFixed(1) }}s
                  </template>
                  <template v-else-if="l.status === 'failed'">
                    <span class="status-dot status-dot--fail"></span>
                    <span :title="l.error_message ?? ''">{{ l.error_code }}</span>
                  </template>
                  <template v-else-if="l.status === 'running'">
                    <span class="status-dot status-dot--running"></span> 运行中
                  </template>
                  <template v-else>
                    <span class="status-dot"></span> 排队
                  </template>
                </span>
              </li>
            </ul>
          </div>
        </section>

        <section v-if="batchDone" class="batch-section batch-section--export">
          <h3 class="batch-section__title">合规导出</h3>
          <p class="hint batch-section__lead" style="margin-top: 0">
            含 <code>COMPLIANCE_README.txt</code>、<code>manifest.json</code>；每条 wav 开头含 AI 节奏标识。
          </p>
          <div v-if="batchSucceeded != null" class="meta-row batch-export-meta">
            <span>成功 {{ batchSucceeded }} 行</span>
            <span v-if="batchFailed" class="meta-row__sep">·</span>
            <span v-if="batchFailed">失败 {{ batchFailed }} 行</span>
          </div>
          <div v-if="batchFailed && batchFailed > 0" class="alert alert--warn" style="margin-top: 12px">
            有 {{ batchFailed }} 行未合成（常见原因：敏感词）。成功行仍在 ZIP 中；失败明细见
            <code>manifest.json</code>。
          </div>
          <a class="btn btn--primary btn--sm" style="margin-top: 14px" :href="exportHref" download>
            下载合规 ZIP
          </a>
        </section>
      </RackPanel>

      <aside class="page-split__side">
        <RackPanel label="指南" title="批量配音怎么做">
          <GuidePanel :steps="[...BATCH_STEPS]">
            <template #step-1>
              <button type="button" class="text-action" @click="showCreate = true">新建项目</button>
            </template>
            <template #step-2>
              <button
                type="button"
                class="text-action"
                :disabled="!selectedProjectId"
                @click="showBind = true"
              >
                绑定角色
              </button>
            </template>
            <template #step-4>
              <a v-if="batchDone" class="text-action" :href="exportHref" download>下载 ZIP</a>
            </template>
          </GuidePanel>
        </RackPanel>

        <RackPanel label="格式" title="CSV 说明">
          <dl class="csv-spec">
            <div class="csv-spec__row">
              <dt>表头</dt>
              <dd><code>role,text</code></dd>
            </div>
            <div class="csv-spec__row">
              <dt>角色列</dt>
              <dd>须与已绑定角色名一致，如 <code>龙宫</code></dd>
            </div>
            <div class="csv-spec__row">
              <dt>台词列</dt>
              <dd>每行一段文本，独立合成</dd>
            </div>
          </dl>
          <a class="text-action" href="/samples/batch_template.csv" download style="margin-top: 12px; display: inline-block">
            下载模板
          </a>
          <p v-if="!versions.length" class="hint warn" style="margin-top: 12px">
            还没有音色版本——请先到训练工作台或智能配音导入权重。
          </p>
          <div v-else class="produce-links" style="margin-top: 8px">
            <button type="button" class="text-action" @click="goLibrary">去智能配音试配</button>
          </div>
        </RackPanel>
      </aside>
      </div>

      <PageActionBar label="相关">
        <PageActionLink @click="showCreate = true">新建项目</PageActionLink>
        <PageActionLink @click="showBind = true">绑定角色</PageActionLink>
        <router-link to="/library" class="page-action-link">智能配音</router-link>
        <router-link to="/discover/feed" class="page-action-link">社区动态</router-link>
      </PageActionBar>
    </PageSurface>

    <AppModal :open="showCreate" label="项目" title="创建项目" @close="showCreate = false">
      <label class="field">
        <span>项目名称</span>
        <input v-model="projectName" placeholder="短剧项目1" />
      </label>
      <template #footer>
        <button type="button" class="btn btn--ghost btn--sm" @click="showCreate = false">取消</button>
        <button type="button" class="btn btn--primary btn--sm" :disabled="busy" @click="onCreateProject">创建</button>
      </template>
    </AppModal>

    <AppModal :open="showBind" label="角色" title="绑定角色" @close="showBind = false">
      <p class="hint modal-hint">CSV 中的 <code>role</code> 列须与角色名一致（如 <code>龙宫</code>）。</p>
      <div class="form-grid">
        <label>角色名<input v-model="roleName" placeholder="龙宫" /></label>
        <label>
          音色版本
          <select v-model="roleVoiceId" :disabled="busy">
            <option v-for="v in versions" :key="v.voice_version_id" :value="v.voice_version_id">
              {{ v.voice_name }} v{{ v.version }}
            </option>
          </select>
        </label>
      </div>
      <p v-if="!versions.length" class="hint warn">还没有音色版本——请先到训练工作台或智能配音导入权重。</p>
      <template #footer>
        <button type="button" class="btn btn--ghost btn--sm" @click="showBind = false">取消</button>
        <button
          type="button"
          class="btn btn--primary btn--sm"
          :disabled="busy || !selectedProjectId || !versions.length"
          @click="onBindRole"
        >
          绑定
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.project-page {
  gap: 12px;
}

.batch-strip {
  margin-bottom: 22px;
}

.batch-section {
  padding-top: 4px;
}

.batch-section + .batch-section {
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid var(--color-line);
}

.batch-section__title {
  margin: 0 0 10px;
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.batch-section__lead {
  margin: 0 0 14px;
}

.upload-zone__title {
  margin: 0 0 6px;
  font-size: 15px;
  font-weight: 500;
  color: var(--color-ink);
}

.upload-zone__sub {
  margin: 0;
}

.batch-log {
  margin-top: 14px;
}

.batch-export-meta {
  margin-top: 4px;
}

.csv-spec {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.csv-spec__row {
  display: grid;
  grid-template-columns: 56px 1fr;
  gap: 8px;
  align-items: baseline;
  font-size: 13px;
}

.csv-spec dt {
  margin: 0;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-brushed-dark);
}

.csv-spec dd {
  margin: 0;
  line-height: 1.5;
  color: var(--color-ink-muted);
}

/* ── 行级详情 ──────────────────────────────── */

.batch-section__header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}

.line-detail-panel {
  margin-top: 12px;
}

.line-summary-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
  padding: 10px 12px;
  background: var(--color-surface);
  border-radius: 8px;
}

.line-stat {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-ink-muted);
}

.line-stat--ok {
  color: #3b9e64;
}

.line-stat--fail {
  color: #d15241;
}

.line-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 320px;
  overflow-y: auto;
}

.line-row {
  display: grid;
  grid-template-columns: 32px 64px 1fr 100px;
  gap: 8px;
  align-items: center;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.4;
}

.line-row:hover {
  background: var(--color-surface);
}

.line-row--succeeded {
  border-left: 2px solid #3b9e64;
}

.line-row--failed {
  border-left: 2px solid #d15241;
  background: rgba(209, 82, 65, 0.06);
}

.line-row--running {
  border-left: 2px solid var(--color-primary);
}

.line-row__idx {
  font-family: monospace;
  font-size: 11px;
  color: var(--color-brushed-dark);
  text-align: right;
}

.line-row__role {
  font-weight: 500;
  color: var(--color-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.line-row__text {
  color: var(--color-ink-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.line-row__status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--color-ink-muted);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-brushed-dark);
  flex-shrink: 0;
}

.status-dot--ok {
  background: #3b9e64;
}

.status-dot--fail {
  background: #d15241;
}

.status-dot--running {
  background: var(--color-primary);
  animation: pulse-dot 1s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
