<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import type { ScriptSegment } from "@/modules/produce/types/script";
import type { VoicePickerItem } from "@/components/VoicePicker.vue";
import { recommendSynthParams } from "@/api/intelligence";
import { applySmartSynthToSegment, formatSmartSynthHint } from "@/modules/produce/utils/smartSynth";

const props = defineProps<{
  segment: ScriptSegment;
  index: number;
  voices: VoicePickerItem[];
  globalSpeed: number;
  globalTemperature: number;
  disabled?: boolean;
  canRemove?: boolean;
}>();

const emit = defineEmits<{
  update: [segment: ScriptSegment];
  remove: [];
  paste: [];
}>();

const sweep = ref(false);
const imprint = ref(false);
const dropHover = ref(false);
let sweepTimer: ReturnType<typeof setTimeout> | undefined;
let imprintTimer: ReturnType<typeof setTimeout> | undefined;

const effectiveSpeed = computed(() => props.segment.speed ?? props.globalSpeed);
const letterSpacing = computed(() => `${Math.max(0.02, 0.14 - (effectiveSpeed.value - 0.5) * 0.08)}em`);

const assignedVoice = computed(() => props.voices.find((v) => v.id === props.segment.voiceVersionId));

const sealChar = computed(() => {
  if (props.segment.characterName) return props.segment.characterName.charAt(0);
  const t = assignedVoice.value?.title?.trim();
  return t ? t.charAt(0) : "";
});

const autoEmotionLoading = ref(false);
const smartHint = ref("");
const areaRef = ref<HTMLTextAreaElement | null>(null);

function resizeArea() {
  const el = areaRef.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.max(96, el.scrollHeight)}px`;
}

watch(
  () => props.segment.text,
  () => {
    void nextTick(resizeArea);
    sweep.value = false;
    void requestAnimationFrame(() => {
      sweep.value = true;
      clearTimeout(sweepTimer);
      sweepTimer = setTimeout(() => {
        sweep.value = false;
      }, 2400);
    });
  },
);

onMounted(() => {
  void nextTick(resizeArea);
});

function onTextInput(e: Event) {
  patch({ text: (e.target as HTMLTextAreaElement).value });
  resizeArea();
}

function patch(partial: Partial<ScriptSegment>) {
  emit("update", { ...props.segment, ...partial });
}

function onVoice(e: Event) {
  patch({ voiceVersionId: (e.target as HTMLSelectElement).value });
  triggerImprint();
}

function triggerImprint() {
  imprint.value = true;
  clearTimeout(imprintTimer);
  imprintTimer = setTimeout(() => {
    imprint.value = false;
  }, 400);
}

function onDragOver(e: DragEvent) {
  if (!e.dataTransfer?.types.includes("application/x-voice-seal")) return;
  e.preventDefault();
  dropHover.value = true;
}

function onDragLeave() {
  dropHover.value = false;
}

function onDrop(e: DragEvent) {
  dropHover.value = false;
  const id = e.dataTransfer?.getData("application/x-voice-seal");
  if (!id) return;
  e.preventDefault();
  patch({ voiceVersionId: id });
  triggerImprint();
}

function previewSweep() {
  sweep.value = true;
  clearTimeout(sweepTimer);
  sweepTimer = setTimeout(() => {
    sweep.value = false;
  }, 2400);
}

async function autoDetectEmotion() {
  const text = props.segment.text.trim();
  if (!text) return;
  autoEmotionLoading.value = true;
  smartHint.value = "";
  try {
    const resp = await recommendSynthParams({
      text,
      character_hint: props.segment.characterName,
    });
    patch(applySmartSynthToSegment(props.segment, resp.result));
    smartHint.value = formatSmartSynthHint(resp.result, resp.mode);
  } catch {
    smartHint.value = "智能分析暂不可用，请稍后重试";
  } finally {
    autoEmotionLoading.value = false;
  }
}
</script>

<template>
  <article
    class="seg-block seg-block--scroll scroll-sunset-sweep"
    :class="{
      'scroll-sunset-sweep--play': sweep,
      'seg-block--drop': dropHover,
      'seg-block--imprint': imprint,
    }"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
  >
    <header class="seg-block__head">
      <div class="seg-block__seal-wrap">
        <span
          v-if="sealChar"
          class="scroll-seal seg-block__seal"
          :class="{ 'seg-block__seal--fresh': imprint }"
          aria-hidden="true"
        >
          {{ sealChar }}
        </span>
        <span v-else class="seg-block__seal-placeholder" title="拖入音色印章">印</span>
      </div>
      <div class="seg-block__meta">
        <span class="rack-label seg-block__role">{{ segment.characterName ?? `段落 ${index + 1}` }}</span>
        <span class="seg-block__chars">{{ segment.text.length }} 字</span>
        <select
          class="seg-block__voice seg-block__voice--ghost"
          :value="segment.voiceVersionId"
          :disabled="disabled"
          @change="onVoice"
        >
          <option v-for="v in voices" :key="v.id" :value="v.id">{{ v.title }}</option>
        </select>
      </div>
      <div class="seg-block__head-actions">
        <button type="button" class="seg-block__preview" title="预览高光动效" :disabled="disabled" @click="previewSweep">
          预览
        </button>
        <button
          v-if="canRemove"
          type="button"
          class="text-action text-action--danger"
          :disabled="disabled"
          @click="emit('remove')"
        >
          删除
        </button>
      </div>
    </header>

    <textarea
      ref="areaRef"
      :value="segment.text"
      class="seg-block__area"
      :style="{ letterSpacing }"
      rows="1"
      placeholder="该段台词…拖入左侧木印或在此书写"
      :disabled="disabled"
      @input="onTextInput"
      @paste="emit('paste')"
    />

    <div class="seg-block__tune seg-block__tune--fine">
      <label class="seg-fine-line">
        <span>语速</span>
        <input
          type="range"
          :value="segment.speed ?? globalSpeed"
          min="0.5"
          max="1.5"
          step="0.05"
          :disabled="disabled"
          @input="patch({ speed: Number(($event.target as HTMLInputElement).value) })"
        />
      </label>
      <label class="seg-fine-line">
        <span>语调</span>
        <input
          type="range"
          :value="segment.temperature ?? globalTemperature"
          min="0.5"
          max="1"
          step="0.02"
          :disabled="disabled"
          @input="patch({ temperature: Number(($event.target as HTMLInputElement).value) })"
        />
      </label>
      <label class="seg-fine-line">
        <span>情感</span>
        <select
          class="seg-fine-select"
          :value="segment.emotion ?? ''"
          :disabled="disabled"
          @change="patch({ emotion: ($event.target as HTMLSelectElement).value || null })"
        >
          <option value="">跟随全局</option>
          <option value="neutral">中性</option>
          <option value="happy">喜</option>
          <option value="angry">怒</option>
          <option value="sad">哀</option>
          <option value="fearful">惧</option>
          <option value="calm">平静</option>
        </select>
        <button
          type="button"
          class="seg-fine-auto-btn"
          :disabled="disabled || autoEmotionLoading || !segment.text.trim()"
          :title="smartHint || (segment.text.trim() ? 'AI 语义分析本段台词，推荐情感与韵律' : '请先输入台词')"
          @click="autoDetectEmotion"
        >
          {{ autoEmotionLoading ? "分析中" : "智能" }}
        </button>
      </label>
      <p v-if="smartHint" class="seg-block__smart-hint">{{ smartHint }}</p>
      <label class="seg-fine-line">
        <span>音调</span>
        <input
          type="range"
          :value="segment.pitch"
          min="0.75"
          max="1.25"
          step="0.05"
          :disabled="disabled"
          @input="patch({ pitch: Number(($event.target as HTMLInputElement).value) })"
        />
      </label>
      <label class="seg-fine-line">
        <span>段间停顿</span>
        <input
          type="range"
          :value="segment.pauseDuration"
          min="0"
          max="5"
          step="0.1"
          :disabled="disabled"
          @input="patch({ pauseDuration: Number(($event.target as HTMLInputElement).value) })"
        />
        <span class="seg-fine-val">{{ segment.pauseDuration.toFixed(1) }}s</span>
      </label>
    </div>
  </article>
</template>

<style scoped>
.seg-block__role {
  font-family: var(--font-scroll);
  letter-spacing: 0.12em;
}

.seg-block__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}

.seg-block__meta {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}

.seg-block__chars {
  font-family: var(--font-mono);
  font-size: 10px;
  color: rgb(107 101 96 / 0.55);
  letter-spacing: 0.04em;
}

.seg-block__head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.seg-block__preview {
  padding: 2px 8px;
  border: none;
  background: transparent;
  font-family: var(--font-scroll);
  font-size: 11px;
  letter-spacing: 0.12em;
  color: rgb(158 90 32 / 0.75);
  cursor: pointer;
}

.seg-block__preview:hover {
  color: rgb(158 90 32);
}

.seg-block__voice--ghost {
  width: 100%;
  flex-basis: 100%;
  margin-top: 4px;
  border: none;
  border-bottom: 1px solid rgb(31 28 25 / 0.1);
  border-radius: 0;
  background: transparent;
  font-family: var(--font-scroll);
  font-size: 11px;
  color: rgb(107 101 96 / 0.65);
  opacity: 0.7;
}

.seg-block__seal-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.1em;
  height: 2.1em;
  border: 1px dashed rgb(192 58 48 / 0.35);
  font-family: var(--font-scroll);
  font-size: 12px;
  color: rgb(192 58 48 / 0.45);
}

.seg-block--drop {
  border-color: rgb(192 58 48 / 0.28) !important;
  background: var(--bg-surface-glass);
}

.seg-block__seal--fresh {
  animation: seal-stamp 0.48s var(--ease-out);
  box-shadow: 0 0 20px rgb(243 192 109 / 0.35);
}

@keyframes seal-stamp {
  0% {
    transform: rotate(-4deg) scale(1.2);
    opacity: 0.4;
  }
  60% {
    transform: rotate(-2deg) scale(0.96);
    opacity: 1;
  }
  100% {
    transform: rotate(-4deg) scale(1);
  }
}

.seg-block__area {
  width: 100%;
  min-height: 96px;
  resize: vertical;
  transition: letter-spacing 0.35s var(--ease-out);
}

.seg-block__tune--fine {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
  padding-top: 12px;
  opacity: 0.72;
}

.seg-fine-line {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 10px;
  letter-spacing: 0.14em;
  color: rgb(107 101 96 / 0.65);
}

.seg-fine-line input[type="range"] {
  -webkit-appearance: none;
  appearance: none;
  height: 1px;
  background: linear-gradient(90deg, rgb(31 28 25 / 0.15), rgb(212 184 120 / 0.45), rgb(31 28 25 / 0.15));
  border-radius: 0;
}

.seg-fine-line input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgb(232 160 80 / 0.85);
  box-shadow: 0 0 6px rgb(243 192 109 / 0.5);
}

.seg-fine-select {
  width: 100%;
  padding: 2px 4px;
  border: none;
  border-bottom: 1px solid rgb(31 28 25 / 0.1);
  border-radius: 0;
  background: transparent;
  font-family: var(--font-scroll);
  font-size: 10px;
  letter-spacing: 0.14em;
  color: rgb(107 101 96 / 0.65);
}

.seg-fine-val {
  font-size: 9px;
  color: rgb(107 101 96 / 0.55);
  margin-top: 2px;
}

.seg-fine-auto-btn {
  margin-top: 2px;
  padding: 1px 6px;
  border: 1px solid rgb(212 184 120 / 0.45);
  border-radius: 4px;
  background: transparent;
  font-family: var(--font-scroll);
  font-size: 9px;
  letter-spacing: 0.12em;
  color: rgb(158 90 32 / 0.65);
  cursor: pointer;
  transition: color 0.2s, border-color 0.2s;
}

.seg-fine-auto-btn:hover:not(:disabled) {
  color: rgb(158 90 32);
  border-color: rgb(212 184 120 / 0.75);
}

.seg-fine-auto-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.seg-block__smart-hint {
  grid-column: 1 / -1;
  margin: 0;
  font-size: 11px;
  line-height: 1.45;
  color: rgb(138 90 36 / 0.9);
}
</style>
