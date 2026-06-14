<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ApiError, exportDownloadUrl, pollJob, synthesize } from "@/api/client";
import { fetchCatalog, publishToCatalog, type CatalogEntry } from "@/api/catalog";
import { fetchVoiceVersions, type VoiceVersionSummary } from "@/api/library";

const router = useRouter();
const entries = ref<CatalogEntry[]>([]);
const myVersions = ref<VoiceVersionSummary[]>([]);
const error = ref("");
const loading = ref(false);
const publishVersionId = ref("");
const publishTitle = ref("蛊真人·龙宫");
const synthText = ref("方源，你给我出来！");
const synthBusy = ref(false);
const aiAck = ref(true);

async function reload() {
  loading.value = true;
  error.value = "";
  try {
    entries.value = await fetchCatalog();
    myVersions.value = await fetchVoiceVersions();
    if (!publishVersionId.value && myVersions.value.length) {
      publishVersionId.value = myVersions.value[0].voice_version_id;
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(reload);

async function onPublish() {
  if (!publishVersionId.value) return;
  error.value = "";
  try {
    await publishToCatalog({
      voice_version_id: publishVersionId.value,
      title: publishTitle.value.trim(),
      description: "平台精选：004 云端微调音色",
      tags: ["短剧", "男声", "反派"],
      featured: true,
    });
    await reload();
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : String(e);
  }
}

async function onTry(entry: CatalogEntry) {
  if (!aiAck.value) return;
  synthBusy.value = true;
  error.value = "";
  try {
    const s = await synthesize(entry.voice_version_id, synthText.value.trim(), aiAck.value);
    const job = await pollJob(s.job_id, undefined, 180_000);
    if (job.status !== "succeeded" || !job.audio_url) {
      throw new Error(job.error_message ?? "合成失败");
    }
    window.open(exportDownloadUrl(s.job_id), "_blank");
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    synthBusy.value = false;
  }
}

function goLibrary(versionId: string) {
  router.push({ path: "/library", query: { version: versionId } });
}
</script>

<template>
  <div>
    <header class="page-hero">
      <h1>音色馆</h1>
      <p>浏览平台精选音色；所有者可将版本发布到馆中供他人合成（MVP+1）。</p>
    </header>

    <div v-if="error" class="alert alert--error">{{ error }}</div>

    <section class="card">
      <h2>发布到音色馆</h2>
      <p class="hint">仅音色所有者可发布；发布后所有登录用户可试听合成。</p>
      <label>
        我的版本
        <select v-model="publishVersionId">
          <option v-for="v in myVersions" :key="v.voice_version_id" :value="v.voice_version_id">
            {{ v.voice_name }} v{{ v.version }}
          </option>
        </select>
      </label>
      <label>
        展示标题
        <input v-model="publishTitle" />
      </label>
      <button class="btn btn--primary" :disabled="loading || !publishVersionId" @click="onPublish">
        发布
      </button>
    </section>

    <section class="card">
      <h2>精选音色</h2>
      <ul v-if="entries.length" class="catalog-list">
        <li v-for="e in entries" :key="e.catalog_id">
          <div class="catalog-item">
            <strong>{{ e.title }}</strong>
            <span v-if="e.featured" class="tag">精选</span>
            <p class="hint">{{ e.description || e.voice_name }}</p>
            <p class="tags">{{ e.tags.join(" · ") }}</p>
            <label class="inline">
              <input v-model="aiAck" type="checkbox" /> 已知晓 AI 合成告知
            </label>
            <div class="row">
              <button
                class="btn btn--primary"
                :disabled="synthBusy || !aiAck"
                @click="onTry(e)"
              >
                试听合成
              </button>
              <button class="btn btn--ghost" @click="goLibrary(e.voice_version_id)">在音色库打开</button>
            </div>
          </div>
        </li>
      </ul>
      <p v-else class="hint">暂无公开音色。可在上方发布你的 004 版本。</p>
    </section>
  </div>
</template>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem;
  margin-top: 1.25rem;
}
label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 0.75rem;
  font-size: 0.85rem;
}
input,
select {
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--border);
  border-radius: 8px;
}
.catalog-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.catalog-item {
  padding: 1rem 0;
  border-bottom: 1px solid var(--border);
}
.tag {
  margin-left: 0.5rem;
  font-size: 0.75rem;
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  background: #fef3c7;
  color: #92400e;
}
.row {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.hint {
  font-size: 0.85rem;
  color: var(--text-muted);
}
.tags {
  font-size: 0.8rem;
  color: var(--text-muted);
}
.inline {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}
</style>
