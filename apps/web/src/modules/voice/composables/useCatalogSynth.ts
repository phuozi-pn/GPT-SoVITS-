import { ref, watch, type Ref } from "vue";
import { exportDownloadUrl, pollJob, synthesize } from "@/api/client";
import type { CatalogEntry } from "@/api/catalog";
import { formatApiError } from "@/utils/apiErrors";
import { buildSynthesisPayload, newSegment } from "@/modules/produce/types/script";

export function useCatalogSynth(
  selectedEntry: Ref<CatalogEntry | null>,
  error: Ref<string>,
  success: Ref<string>,
) {
  const segments = ref([newSegment("", "方源，你给我出来！")]);
  const multiMode = ref(false);
  const catalogVoiceId = ref("");
  const speed = ref(1.05);
  const temperature = ref(0.78);
  const synthBusy = ref(false);
  const aiAck = ref(true);
  const catalogAudioUrl = ref("");
  const catalogExportJobId = ref("");

  watch(selectedEntry, (entry) => {
    if (!entry) return;
    catalogVoiceId.value = entry.voice_version_id;
    if (!multiMode.value) {
      segments.value = segments.value.map((s) => ({
        ...s,
        voiceVersionId: entry.voice_version_id,
      }));
    }
  });

  async function onCatalogSynth() {
    const target = selectedEntry.value;
    if (!target) {
      error.value = "先从左侧选一个音色，再输入台词试听";
      return;
    }
    if (!target.can_use) {
      error.value = target.price_cents > 0 ? "请先购买授权后再合成" : "当前音色不可使用";
      return;
    }
    if (!aiAck.value) return;
    const text = segments.value.map((s) => s.text).join("").trim();
    if (!text) {
      error.value = "请填写试听台词";
      return;
    }
    synthBusy.value = true;
    error.value = "";
    success.value = "";
    catalogAudioUrl.value = "";
    catalogExportJobId.value = "";
    try {
      const payload = buildSynthesisPayload(segments.value, {
        speed: speed.value,
        temperature: temperature.value,
        emotion: null,
        emotionStrength: 0.5,
      });
      const s = await synthesize(payload, aiAck.value);
      catalogExportJobId.value = s.job_id;
      const job = await pollJob(s.job_id, undefined, 180_000);
      if (job.status !== "succeeded" || !job.audio_url) {
        throw new Error(job.error_message ?? "合成失败");
      }
      catalogAudioUrl.value = job.audio_url;
      success.value = `试听合成完成：${target.title}`;
    } catch (e) {
      error.value = formatApiError(e);
    } finally {
      synthBusy.value = false;
    }
  }

  return {
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
  };
}
