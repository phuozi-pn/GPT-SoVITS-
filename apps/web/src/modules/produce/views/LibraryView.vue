<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { ApiError, pollJob, synthesize, exportDownloadUrl } from "@/api/client";
import {
  fetchVoiceVersions,
  importEngineWeights,
  type ImportWeightsBody,
  type VoiceVersionSummary,
} from "@/api/library";
import HistoryCard from "@/components/HistoryCard.vue";
import AppModal from "@/components/AppModal.vue";
import EmptyGuide from "@/components/EmptyGuide.vue";
import ErrorBanner from "@/components/ErrorBanner.vue";
import HelpHint from "@/components/HelpHint.vue";
import PageActionBar from "@/components/PageActionBar.vue";
import PageActionLink from "@/components/PageActionLink.vue";
import PageHero from "@/components/PageHero.vue";
import PageSurface from "@/components/PageSurface.vue";
import { getPageMeta } from "@/config/navigation";
import { formatApiError } from "@/utils/apiErrors";
import { useToast } from "@/composables/useToast";
import { buildSynthesisPayload, newSegment } from "@/modules/produce/types/script";
import MakeWorkspace from "@/modules/produce/components/MakeWorkspace.vue";
import ProduceSceneGuide, { type ProduceScene } from "@/modules/produce/components/ProduceSceneGuide.vue";

type HistoryItem = {
  id: string;
  title: string;
  subtitle: string;
  textPreview: string;
  audioUrl: string;
  createdAt: string;
};

const pageMeta = getPageMeta("/library", "library");
const { toastOk } = useToast();

const versions = ref<VoiceVersionSummary[]>([]);
const loading = ref(false);
const error = ref("");
const history = ref<HistoryItem[]>([]);

const synthVersionId = ref("");
const segments = ref([newSegment("", "方源，你给我出来！")]);
const multiMode = ref(false);
const produceScene = ref<ProduceScene>("single");
const aiDisclosureAck = ref(true);
const audioUrl = ref("");
const lastSynthJobId = ref("");
const synthBusy = ref(false);
const speed = ref(1.05);
const temperature = ref(0.78);
const emotion = ref<string | null>(null);
const emotionStrength = ref(0.5);
const showImport = ref(false);

const importForm = ref<ImportWeightsBody>({
  voice_name: "",
  label: "",
  engine_gpt_weights: "",
  engine_sovits_weights: "",
  ref_audio_host_path: "",
  ref_text: "",
  text_split_method: "cut0",
  temperature: 0.78,
  speed_factor: 1.05,
  top_p: 1.0,
});

const pickerItems = computed(() =>
  versions.value.map((v) => ({
    id: v.voice_version_id,
    title: v.voice_name,
    subtitle: `v${v.version} · ${v.voice_version_id.slice(0, 8)}…`,
    tags: [v.label, v.imported ? "已导入" : "", v.granted ? "已授权" : ""].filter(Boolean) as string[],
    badge: v.granted ? "授权" : v.imported ? "导入" : undefined,
  })),
);

const selectedVoice = computed(() => versions.value.find((v) => v.voice_version_id === synthVersionId.value));
const selectedPicker = computed(() => pickerItems.value.find((p) => p.id === synthVersionId.value));
const hasVoices = computed(() => versions.value.length > 0);

function pushHistory(voice: VoiceVersionSummary, text: string, url: string) {
  history.value.unshift({
    id: `${Date.now()}`,
    title: `${voice.voice_name} · v${voice.version}`,
    subtitle: voice.label ?? "",
    textPreview: text.slice(0, 80),
    audioUrl: url,
    createdAt: new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" }),
  });
  if (history.value.length > 12) history.value.pop();
}

async function reload() {
  loading.value = true;
  error.value = "";
  try {
    versions.value = await fetchVoiceVersions();
    if (!synthVersionId.value && versions.value.length) {
      synthVersionId.value = versions.value[0].voice_version_id;
    }
    if (segments.value.length && !segments.value[0].voiceVersionId) {
      segments.value[0].voiceVersionId = synthVersionId.value;
    }
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
}

onMounted(reload);

watch(synthVersionId, (id) => {
  if (!id || multiMode.value) return;
  if (segments.value.length === 1) {
    segments.value[0].voiceVersionId = id;
  }
});

watch(produceScene, (scene) => {
  if (scene === "dialogue" || scene === "vocal") multiMode.value = true;
  else if (scene === "single") multiMode.value = false;
});

watch(multiMode, (on) => {
  if (on && produceScene.value === "single") produceScene.value = "dialogue";
  if (!on && (produceScene.value === "dialogue" || produceScene.value === "vocal")) {
    produceScene.value = "single";
  }
});

const generateLabel = computed(() =>
  produceScene.value === "vocal" ? "生成念唱预览" : "开始生成语音",
);

async function onImport() {
  error.value = "";
  loading.value = true;
  try {
    const v = await importEngineWeights(importForm.value);
    toastOk(`已导入 ${v.voice_name} v${v.version}`);
    synthVersionId.value = v.voice_version_id;
    showImport.value = false;
    await reload();
  } catch (e) {
    error.value = e instanceof ApiError ? formatApiError(e) : formatApiError(e);
  } finally {
    loading.value = false;
  }
}

async function onSynth() {
  if (!synthVersionId.value || !aiDisclosureAck.value) return;
  const voice = selectedVoice.value;
  error.value = "";
  audioUrl.value = "";
  lastSynthJobId.value = "";
  synthBusy.value = true;
  try {
    const payload = buildSynthesisPayload(segments.value, {
      speed: speed.value,
      temperature: temperature.value,
      emotion: emotion.value,
      emotionStrength: emotionStrength.value,
    });
    const text = segments.value.map((s) => s.text).join("");
    const s = await synthesize(payload, aiDisclosureAck.value);
    lastSynthJobId.value = s.job_id;
    const job = await pollJob(s.job_id, undefined, 180_000);
    if (job.status !== "succeeded" || !job.audio_url) {
      throw new Error(job.error_message ?? "合成未完成，请检查引擎是否在 9880 端口运行。");
    }
    audioUrl.value = job.audio_url;
    toastOk("生成完成——可在调音区返听并导出");
    if (voice) pushHistory(voice, text, job.audio_url);
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    synthBusy.value = false;
  }
}

function loadFromHistory(item: HistoryItem) {
  audioUrl.value = item.audioUrl;
  segments.value = [newSegment(synthVersionId.value, item.textPreview)];
  multiMode.value = false;
  produceScene.value = "single";
}
</script>

<template>
  <div class="library-make page page--fill">
    <ErrorBanner
      v-if="error"
      :message="error"
      retry
      :loading="loading"
      @retry="reload"
      @dismiss="error = ''"
    />

    <PageSurface>
      <PageHero compact flow title="智能配音" :hint="pageMeta.desc">
        <template #stats>
          <p class="page-metrics">
            可用音色 <strong>{{ versions.length }}</strong>
            <template v-if="history.length"> · 最近生成 <strong>{{ history.length }}</strong></template>
          </p>
        </template>
        <template #actions>
          <div class="hero-actions">
            <span class="row-actions">
              <router-link to="/projects" class="text-action">短剧批量配音</router-link>
              <span class="row-actions__sep" aria-hidden="true">·</span>
              <button type="button" class="text-action" @click="showImport = true">导入权重</button>
              <span class="row-actions__sep" aria-hidden="true">·</span>
              <button type="button" class="text-action" :disabled="loading" @click="reload">刷新</button>
            </span>
          </div>
        </template>
      </PageHero>

      <ProduceSceneGuide v-model:scene="produceScene" />

      <HelpHint
        v-if="hasVoices"
        icon="💡"
        text="选择一个音色，输入文本或粘贴剧本，点击生成即可。支持多人情景对话——粘贴带角色前缀的剧本，AI 会自动识别分段。"
        closable
      />

      <p v-if="produceScene === 'vocal'" class="produce-vocal-note" role="note">
        实验性念唱预览：基于说话合成引擎，非专业歌声；正式演唱需旋律引擎与歌唱授权素材。
      </p>

      <EmptyGuide
        v-if="!loading && !hasVoices"
        title="还没有可用音色"
        desc="训练自有声纹，或从音色馆购买授权后，即可开始单人朗读、多人情景与歌曲分段念唱。"
      >
        <template #actions>
          <router-link to="/studio" class="btn-formal btn-formal--primary">去训练工作台</router-link>
          <router-link to="/catalog" class="btn-formal">浏览音色馆</router-link>
        </template>
        <template #extra>
          新手提示：也可以从「导入权重」加载已有训练产物
        </template>
      </EmptyGuide>

      <p v-if="loading && hasVoices" class="hint library-loading-hint" role="status">正在刷新音色列表…</p>

      <div v-else class="library-make-panel">
        <MakeWorkspace
          v-model:segments="segments"
          v-model:multi-mode="multiMode"
          v-model:voice-id="synthVersionId"
          v-model:ai-ack="aiDisclosureAck"
          v-model:speed="speed"
          v-model:temperature="temperature"
          v-model:emotion="emotion"
          v-model:emotion-strength="emotionStrength"
          :work-mode="produceScene"
          :voices="pickerItems"
          :voice-title="selectedPicker?.title"
          :voice-subtitle="selectedPicker?.subtitle"
          :voice-badge="selectedPicker?.badge"
          :voice-count="versions.length"
          :busy="synthBusy"
          :audio-url="audioUrl"
          :export-href="lastSynthJobId ? exportDownloadUrl(lastSynthJobId) : undefined"
          :generate-label="generateLabel"
          @generate="onSynth"
          @reload="reload"
        />
      </div>

      <section v-if="history.length" class="history-section">
        <div class="section-head">
          <div>
            <h2 class="section-head__title">最近生成</h2>
            <p class="section-head__hint">点击条目可回填台本并返听</p>
          </div>
          <span class="section-head__meta">{{ history.length }} 条记录</span>
        </div>
        <div class="history-grid">
          <HistoryCard
            v-for="item in history"
            :key="item.id"
            :title="item.title"
            :subtitle="item.subtitle"
            :text-preview="item.textPreview"
            :audio-url="item.audioUrl"
            :created-at="item.createdAt"
            @select="loadFromHistory(item)"
          />
        </div>
      </section>

      <PageActionBar label="相关">
        <router-link to="/projects" class="page-action-link">短剧批量配音</router-link>
        <router-link to="/voices" class="page-action-link">我的音色</router-link>
        <PageActionLink @click="showImport = true">导入引擎权重</PageActionLink>
        <router-link to="/studio" class="page-action-link">训练工作台</router-link>
        <router-link to="/catalog" class="page-action-link">音色馆</router-link>
      </PageActionBar>
    </PageSurface>

    <AppModal :open="showImport" label="导入" title="导入引擎权重" wide @close="showImport = false">
      <p class="hint modal-hint">将云端训练产物导入本地引擎，供合成与发布使用。</p>
      <div class="legacy-form-grid">
        <label class="field">音色名<input v-model="importForm.voice_name" /></label>
        <label class="field">标签<input v-model="importForm.label" /></label>
        <label class="field">GPT 权重<input v-model="importForm.engine_gpt_weights" /></label>
        <label class="field">SoVITS 权重<input v-model="importForm.engine_sovits_weights" /></label>
        <label class="field">ref wav<input v-model="importForm.ref_audio_host_path" /></label>
        <label class="field legacy-span-2">ref 文本<input v-model="importForm.ref_text" /></label>
      </div>
      <template #footer>
        <button type="button" class="btn btn--ghost btn--sm" @click="showImport = false">取消</button>
        <button type="button" class="btn btn--primary btn--sm" :disabled="loading" @click="onImport">导入权重</button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.library-make {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.library-loading-hint {
  text-align: center;
  padding: 24px 0;
  color: var(--color-ink-muted);
}

.library-make-panel {
  min-height: 0;
}

.produce-vocal-note {
  margin: 0 0 12px;
  padding: 10px 14px;
  border: 1px solid rgb(212 146 74 / 0.35);
  border-radius: var(--radius-ui);
  background: rgb(212 146 74 / 0.08);
  font-size: 13px;
  line-height: 1.5;
  color: #e0b060;
}

.history-section {
  margin-top: 0;
}

.history-grid {
  display: grid;
  gap: 12px;
}

@media (min-width: 640px) {
  .history-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (min-width: 1100px) {
  .history-grid {
    grid-template-columns: 1fr 1fr 1fr;
  }
}
</style>
