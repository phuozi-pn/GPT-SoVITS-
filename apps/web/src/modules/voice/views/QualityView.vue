<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  evaluateQuality,
  fetchAbTrial,
  fetchQualityReport,
  submitAbVote,
  type AbTrial,
  type QualityReport,
} from "@/api/quality";
import PageHero from "@/components/PageHero.vue";
import PageSurface from "@/components/PageSurface.vue";
import RackPanel from "@/modules/voice/components/studio/RackPanel.vue";
import TapePlayer from "@/modules/voice/components/studio/TapePlayer.vue";
import VoiceCloneCompare from "@/components/VoiceCloneCompare.vue";
import { formatApiError } from "@/utils/apiErrors";

const route = useRoute();
const router = useRouter();
const report = ref<QualityReport | null>(null);
const trial = ref<AbTrial | null>(null);
const loading = ref(false);
const error = ref("");
const success = ref("");
const abScore = ref(4);

const voiceVersionId = computed(() => String(route.params.voiceVersionId ?? ""));
const scorePercent = computed(() =>
  report.value ? `${(report.value.similarity_score * 100).toFixed(1)}%` : "—",
);
const passLabel = computed(() => {
  if (!report.value) return "待评测";
  return report.value.quality_pass ? "已通过" : "未达标";
});

async function loadReport() {
  if (!voiceVersionId.value) return;
  loading.value = true;
  error.value = "";
  try {
    report.value = await fetchQualityReport(voiceVersionId.value);
  } catch {
    report.value = null;
  } finally {
    loading.value = false;
  }
}

async function onEvaluate() {
  if (!voiceVersionId.value) return;
  loading.value = true;
  error.value = "";
  success.value = "";
  try {
    report.value = await evaluateQuality(voiceVersionId.value);
    success.value = report.value.quality_pass ? "测评通过，可进入 AB 试听" : "测评未达阈值";
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
}

async function onStartAb() {
  if (!voiceVersionId.value) return;
  error.value = "";
  success.value = "";
  try {
    trial.value = await fetchAbTrial(voiceVersionId.value);
  } catch (e) {
    error.value = formatApiError(e);
  }
}

async function onVote(slot: "a" | "b") {
  if (!trial.value) return;
  error.value = "";
  try {
    const result = await submitAbVote(voiceVersionId.value, {
      pick_slot: slot,
      slot_a_kind: trial.value.slot_a_kind,
      slot_b_kind: trial.value.slot_b_kind,
      score: abScore.value,
    });
    success.value = result.message;
    await loadReport();
    trial.value = null;
  } catch (e) {
    error.value = formatApiError(e);
  }
}

onMounted(loadReport);
watch(voiceVersionId, loadReport);
</script>

<template>
  <div class="page page--full quality-page">
    <div v-if="error" class="alert alert--error">{{ error }}</div>
    <div v-if="success" class="alert alert--ok">{{ success }}</div>

    <PageSurface>
      <PageHero compact flow hint="训练完成后可在此查看相似度报告并进行 AB 盲听投票。">
      <template #stats>
        <p class="page-metrics">
          相似度 <strong :class="report?.quality_pass ? 'page-metrics__ok' : 'page-metrics__accent'">{{ scorePercent }}</strong>
          · 状态 <strong>{{ passLabel }}</strong>
          <template v-if="report?.ab_vote_count"> · AB 投票 <strong>{{ report.ab_vote_count }}</strong></template>
        </p>
      </template>
      <template #actions>
        <div class="hero-actions">
          <button class="text-action" @click="router.push('/studio')">返回工作台</button>
          <button class="btn btn--primary btn--sm" :disabled="loading" @click="onEvaluate">重新评测</button>
        </div>
      </template>
      </PageHero>

      <RackPanel label="质量" title="相似度报告">
      <p v-if="loading && !report" class="hint">加载中…</p>
      <template v-else-if="report">
        <VoiceCloneCompare
          v-if="report.ref_audio_url || report.synth_audio_url"
          class="quality-compare"
          :source-audio-url="report.ref_audio_url"
          :clone-demo-audio-url="report.synth_audio_url"
        />
        <div class="quality-hero">
          <p class="page-metrics">
            Score
            <strong :class="report.quality_pass ? 'page-metrics__ok' : 'page-metrics__danger'">{{ scorePercent }}</strong>
          </p>
          <p class="hint" style="margin: 0">
            阈值 {{ (report.threshold * 100).toFixed(0) }}% · 方法 {{ report.method }} ·
            <span v-if="report.ab_vote_count">
              选原素材比例
              {{ report.ref_pick_rate != null ? (report.ref_pick_rate * 100).toFixed(0) + "%" : "—" }}
            </span>
          </p>
        </div>
      </template>
      <p v-else class="hint">尚无测评报告——训练完成后会自动评测，或点击右上角手动触发。</p>
      </RackPanel>

      <RackPanel label="AB" title="盲听对比">
      <p class="hint modal-hint">{{ trial?.instruction ?? "开始盲听后，系统将随机排列原素材与合成样例。" }}</p>
      <button v-if="!trial" class="btn btn--primary btn--sm" :disabled="!report" @click="onStartAb">
        开始 AB 试听
      </button>
      <div v-else class="ab-grid">
        <div class="ab-slot">
          <h3 class="subhead" style="margin-top: 0">A</h3>
          <TapePlayer :src="trial.audio_a_url" :height="72" />
          <button class="text-action" style="margin-top: 10px" @click="onVote('a')">选 A</button>
        </div>
        <div class="ab-slot">
          <h3 class="subhead" style="margin-top: 0">B</h3>
          <TapePlayer :src="trial.audio_b_url" :height="72" />
          <button class="text-action" style="margin-top: 10px" @click="onVote('b')">选 B</button>
        </div>
      </div>
      <label v-if="trial" style="display: block; margin-top: 12px; max-width: 200px">
        主观评分 (1–5)
        <input v-model.number="abScore" type="number" min="1" max="5" />
      </label>
      </RackPanel>
    </PageSurface>
  </div>
</template>

<style scoped>
.quality-page {
  gap: 12px;
}

.quality-compare {
  margin-bottom: 16px;
}
</style>
