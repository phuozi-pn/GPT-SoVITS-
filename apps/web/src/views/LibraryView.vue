<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ApiError, pollJob, synthesize } from "@/api/client";
import {
  fetchVoiceVersions,
  importEngineWeights,
  type ImportWeightsBody,
  type VoiceVersionSummary,
} from "@/api/library";

const versions = ref<VoiceVersionSummary[]>([]);
const loading = ref(false);
const error = ref("");
const success = ref("");

const synthVersionId = ref("");
const synthText = ref("方源，你给我出来！");
const audioUrl = ref("");
const synthBusy = ref(false);

const importForm = ref<ImportWeightsBody>({
  voice_name: "蛊真人-004",
  label: "cloud-004",
  engine_gpt_weights: "GPT_weights_v2Pro/cloud_guzhenren-004-e8.ckpt",
  engine_sovits_weights: "SoVITS_weights_v2Pro/cloud_guzhenren-004_e8_s400.pth",
  ref_audio_host_path: "C:\\Users\\panta\\Desktop\\ref_guzhenren.wav",
  ref_text: "龙宫傲然一笑，宿命谷从来都不能被古仙运用。",
  text_split_method: "cut0",
  temperature: 0.78,
});

async function reload() {
  loading.value = true;
  error.value = "";
  try {
    versions.value = await fetchVoiceVersions();
    if (!synthVersionId.value && versions.value.length) {
      synthVersionId.value = versions.value[0].voice_version_id;
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(reload);

async function onImport() {
  error.value = "";
  success.value = "";
  loading.value = true;
  try {
    const v = await importEngineWeights(importForm.value);
    success.value = `已导入 ${v.voice_name} v${v.version} → ${v.voice_version_id}`;
    synthVersionId.value = v.voice_version_id;
    await reload();
  } catch (e) {
    error.value = e instanceof ApiError ? `${e.code}: ${e.message}` : String(e);
  } finally {
    loading.value = false;
  }
}

async function onSynth() {
  if (!synthVersionId.value) return;
  error.value = "";
  audioUrl.value = "";
  synthBusy.value = true;
  try {
    const s = await synthesize(synthVersionId.value, synthText.value.trim());
    const job = await pollJob(s.job_id, undefined, 180_000);
    if (job.status !== "succeeded" || !job.audio_url) {
      throw new Error(job.error_message ?? "合成失败");
    }
    audioUrl.value = job.audio_url;
    success.value = "合成完成";
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    synthBusy.value = false;
  }
}
</script>

<template>
  <div>
    <header class="page-hero">
      <h1>音色库</h1>
      <p>导入云端权重后，在此选择版本直接合成（需 9880 引擎运行）。</p>
    </header>

    <div v-if="error" class="alert alert--error">{{ error }}</div>
    <div v-if="success" class="alert alert--ok">{{ success }}</div>

    <section class="card">
      <h2>导入引擎权重</h2>
      <p class="hint">权重文件需在 <code>ENGINE_TRAIN_ROOT</code> 下；ref 为本机 wav 绝对路径。</p>
      <div class="form-grid">
        <label>音色名<input v-model="importForm.voice_name" /></label>
        <label>标签<input v-model="importForm.label" /></label>
        <label>GPT 权重<input v-model="importForm.engine_gpt_weights" /></label>
        <label>SoVITS 权重<input v-model="importForm.engine_sovits_weights" /></label>
        <label>ref wav 路径<input v-model="importForm.ref_audio_host_path" /></label>
        <label class="span-2">ref 文本<input v-model="importForm.ref_text" /></label>
      </div>
      <button class="btn btn--primary" :disabled="loading" @click="onImport">导入到平台</button>
    </section>

    <section class="card">
      <h2>我的版本</h2>
      <button class="btn btn--ghost" :disabled="loading" @click="reload">刷新</button>
      <ul v-if="versions.length" class="version-list">
        <li v-for="v in versions" :key="v.voice_version_id">
          <strong>{{ v.voice_name }}</strong> v{{ v.version }}
          <span v-if="v.label" class="tag">{{ v.label }}</span>
          <span v-if="v.imported" class="tag tag--ok">已导入</span>
          <code class="mono">{{ v.voice_version_id }}</code>
        </li>
      </ul>
      <p v-else class="hint">暂无版本，请先导入或完成训练。</p>
    </section>

    <section class="card">
      <h2>快速合成</h2>
      <label>
        选择版本
        <select v-model="synthVersionId">
          <option v-for="v in versions" :key="v.voice_version_id" :value="v.voice_version_id">
            {{ v.voice_name }} v{{ v.version }} {{ v.label ? `(${v.label})` : "" }}
          </option>
        </select>
      </label>
      <label>
        台词
        <textarea v-model="synthText" rows="3" />
      </label>
      <button class="btn btn--primary" :disabled="synthBusy || !synthVersionId" @click="onSynth">
        {{ synthBusy ? "合成中…" : "合成试听" }}
      </button>
      <audio v-if="audioUrl" controls :src="audioUrl" class="audio-player" />
      <p v-if="audioUrl" class="hint"><a :href="audioUrl" download>下载 wav</a></p>
    </section>
  </div>
</template>

<style scoped>
.page-hero h1 {
  margin: 0 0 0.35rem;
}
.page-hero p {
  margin: 0;
  color: var(--text-muted);
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem;
  margin-top: 1.25rem;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin: 1rem 0;
}
.form-grid label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.85rem;
}
.span-2 {
  grid-column: span 2;
}
input,
select,
textarea {
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--border);
  border-radius: 8px;
}
.version-list {
  list-style: none;
  padding: 0;
  margin: 0.75rem 0 0;
}
.version-list li {
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--border);
}
.mono {
  display: block;
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
}
.tag {
  margin-left: 0.5rem;
  font-size: 0.75rem;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  background: var(--border);
}
.tag--ok {
  background: #dcfce7;
  color: #166534;
}
.audio-player {
  display: block;
  width: 100%;
  margin-top: 1rem;
}
.alert--ok {
  background: #ecfdf5;
  border-color: #6ee7b7;
  color: #065f46;
}
.hint {
  font-size: 0.85rem;
  color: var(--text-muted);
}
</style>
