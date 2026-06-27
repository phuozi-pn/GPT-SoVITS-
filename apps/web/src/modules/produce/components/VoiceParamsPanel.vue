<script setup lang="ts">
import { computed, ref } from "vue";
import TapePlayer from "@/modules/voice/components/studio/TapePlayer.vue";
import { analyzeEmotion } from "@/api/client";
import { recommendSynthParams } from "@/api/intelligence";

const props = defineProps<{
  voiceTitle?: string;
  voiceSubtitle?: string;
  voiceBadge?: string;
  busy?: boolean;
  audioUrl?: string;
  exportHref?: string;
  embedded?: boolean;
  compact?: boolean;
  docked?: boolean;
  referenceText?: string;
  characterHint?: string;
}>();

const speed = defineModel<number>("speed", { default: 1.05 });
const temperature = defineModel<number>("temperature", { default: 0.78 });
const emotion = defineModel<string | null>("emotion", { default: null });
const emotionStrength = defineModel<number>("emotionStrength", { default: 0.5 });

const EMOTION_OPTIONS = [
  { value: "", label: "默认", icon: "—" },
  { value: "neutral", label: "中性", icon: "中" },
  { value: "happy", label: "喜悦", icon: "喜" },
  { value: "angry", label: "愤怒", icon: "怒" },
  { value: "sad", label: "哀伤", icon: "哀" },
  { value: "fearful", label: "恐惧", icon: "惧" },
  { value: "calm", label: "平静", icon: "静" },
];

const avatar = computed(() => {
  const t = props.voiceTitle?.trim();
  return t ? t.charAt(0) : "音";
});

const showVoiceHead = computed(() => !props.embedded && !props.compact);

const autoEmotionLoading = ref(false);
const autoEmotionError = ref("");
const smartReasoning = ref("");

async function autoDetectEmotion() {
  const text = props.referenceText?.trim();
  if (!text) {
    autoEmotionError.value = "无参考文本可供分析";
    return;
  }
  autoEmotionLoading.value = true;
  autoEmotionError.value = "";
  smartReasoning.value = "";
  try {
    const smart = await recommendSynthParams({
      text,
      character_hint: props.characterHint,
    });
    if (smart.mode === "llm") {
      emotion.value = smart.result.emotion;
      emotionStrength.value = smart.result.emotion_strength;
      speed.value = smart.result.speed_factor;
      temperature.value = smart.result.temperature;
      smartReasoning.value = smart.result.reasoning;
    } else {
      const result = await analyzeEmotion(text);
      emotion.value = result.emotion;
      emotionStrength.value = result.strength;
    }
  } catch {
    try {
      const result = await analyzeEmotion(text);
      emotion.value = result.emotion;
      emotionStrength.value = result.strength;
    } catch (err2: unknown) {
      autoEmotionError.value = err2 instanceof Error ? err2.message : "分析暂不可用";
    }
  } finally {
    autoEmotionLoading.value = false;
  }
}

function speedLabel(v: number): string {
  if (v < 0.8) return "慢速";
  if (v < 0.95) return "较慢";
  if (v < 1.05) return "正常";
  if (v < 1.2) return "较快";
  return "快速";
}

function tempLabel(v: number): string {
  if (v < 0.6) return "稳定";
  if (v < 0.8) return "较稳";
  if (v < 0.9) return "适中";
  return "丰富";
}
</script>

<template>
  <div
    class="voice-params"
    :class="{
      'voice-params--compact': compact,
      'voice-params--embedded': embedded,
      'voice-params--docked': docked,
    }"
  >
    <!-- 音色头部 -->
    <header v-if="showVoiceHead" class="vp-head">
      <div class="vp-head__avatar" aria-hidden="true">{{ avatar }}</div>
      <div class="vp-head__meta">
        <p class="vp-head__label">当前音色</p>
        <h3 class="vp-head__title">{{ voiceTitle ?? "请选择音色" }}</h3>
        <p v-if="voiceSubtitle" class="vp-head__sub">{{ voiceSubtitle }}</p>
        <span v-if="voiceBadge" class="vp-head__badge">{{ voiceBadge }}</span>
      </div>
    </header>

    <!-- 嵌入模式标题 -->
    <header v-else-if="embedded" class="vp-dock-head">
      <h4 class="vp-dock-head__title">合成参数</h4>
      <p v-if="voiceTitle" class="vp-dock-head__voice">
        {{ voiceTitle }}
        <span v-if="voiceBadge" class="vp-head__badge">{{ voiceBadge }}</span>
      </p>
    </header>

    <!-- 参数滑块区 -->
    <section
      class="vp-sliders"
      :class="{
        'vp-sliders--row': compact && !embedded,
        'vp-sliders--col': embedded || !compact,
      }"
    >
      <!-- 语速 -->
      <div class="vp-field">
        <div class="vp-field__bar">
          <span class="vp-field__label">语速</span>
          <span class="vp-field__value">
            {{ speed.toFixed(2) }}
            <span class="vp-field__tag">{{ speedLabel(speed) }}</span>
          </span>
        </div>
        <input
          v-model.number="speed"
          type="range"
          min="0.5"
          max="1.5"
          step="0.05"
          :disabled="busy"
          class="vp-range"
        />
        <div class="vp-field__ticks">
          <span>0.5</span>
          <span>1.0</span>
          <span>1.5</span>
        </div>
      </div>

      <!-- 温度 -->
      <div class="vp-field">
        <div class="vp-field__bar">
          <span class="vp-field__label">温度</span>
          <span class="vp-field__value">
            {{ temperature.toFixed(2) }}
            <span class="vp-field__tag">{{ tempLabel(temperature) }}</span>
          </span>
        </div>
        <input
          v-model.number="temperature"
          type="range"
          min="0.5"
          max="1"
          step="0.02"
          :disabled="busy"
          class="vp-range"
        />
        <div class="vp-field__ticks">
          <span>稳定</span>
          <span>适中</span>
          <span>丰富</span>
        </div>
      </div>

      <!-- 情感选择 -->
      <div class="vp-field vp-field--emotion">
        <div class="vp-field__bar">
          <span class="vp-field__label">情感</span>
          <span class="vp-field__value vp-field__value--text">
            {{ EMOTION_OPTIONS.find((o) => o.value === emotion)?.label ?? "默认" }}
          </span>
        </div>
        <div class="vp-emotion-grid">
          <button
            v-for="opt in EMOTION_OPTIONS"
            :key="opt.value"
            type="button"
            class="vp-emotion-btn"
            :class="{ 'vp-emotion-btn--on': (opt.value || null) === emotion }"
            :disabled="busy"
            @click="emotion = opt.value || null"
            :title="opt.label"
          >
            <span class="vp-emotion-btn__glyph">{{ opt.icon }}</span>
            <span class="vp-emotion-btn__text">{{ opt.label }}</span>
          </button>
        </div>

        <!-- 智能推荐（去AI感，融入为"参考"） -->
        <div class="vp-reference">
          <button
            type="button"
            class="vp-ref-btn"
            :class="{ 'vp-ref-btn--loading': autoEmotionLoading }"
            :disabled="busy || autoEmotionLoading || !referenceText"
            @click="autoDetectEmotion"
          >
            {{ autoEmotionLoading ? "分析中…" : "根据文稿自动推荐参数" }}
          </button>

          <Transition name="reason-fade">
            <div v-if="smartReasoning" class="vp-ref-reason">
              <p class="vp-ref-reason__text">{{ smartReasoning }}</p>
            </div>
          </Transition>

          <p v-if="autoEmotionError" class="vp-ref-error">{{ autoEmotionError }}</p>
        </div>
      </div>

      <!-- 情感强度 -->
      <Transition name="reason-fade">
        <div v-if="emotion" class="vp-field">
          <div class="vp-field__bar">
            <span class="vp-field__label">情感强度</span>
            <span class="vp-field__value">{{ emotionStrength.toFixed(1) }}</span>
          </div>
          <input
            v-model.number="emotionStrength"
            type="range"
            min="0"
            max="1"
            step="0.1"
            :disabled="busy"
            class="vp-range"
          />
        </div>
      </Transition>
    </section>

    <!-- 试听区 -->
    <section v-if="audioUrl" class="vp-playback">
      <div class="vp-playback__bar">
        <span class="vp-playback__label">试听</span>
        <a v-if="exportHref" :href="exportHref" download class="vp-playback__export">
          导出音频 ↓
        </a>
      </div>
      <div class="vp-playback__player">
        <TapePlayer :src="audioUrl" :height="48" />
      </div>
    </section>
  </div>
</template>

<style scoped>
/* ── 容器 ─────────────────────────────────────────── */
.voice-params {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px 20px;
}

.voice-params--embedded { gap: 16px; padding: 18px 20px; }
.voice-params--compact { gap: 14px; padding: 16px 18px; }

/* ── 音色头部 ─────────────────────────────────────── */
.vp-head {
  display: flex;
  gap: 14px;
  align-items: center;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--color-line);
}

.vp-head__avatar {
  display: flex;
  height: 44px;
  width: 44px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: linear-gradient(135deg, #b8965c 0%, #8a6a3a 100%);
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  box-shadow: 0 2px 6px rgb(160 120 60 / 0.3);
}

.vp-head__meta { flex: 1; min-width: 0; }

.vp-head__label {
  margin: 0;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-ink-faint);
}

.vp-head__title {
  margin: 2px 0 0;
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--color-ink);
}

.vp-head__sub {
  margin: 2px 0 0;
  font-size: 11px;
  color: var(--color-ink-muted);
  word-break: break-all;
}

.vp-head__badge {
  display: inline-flex;
  margin-top: 4px;
  padding: 1px 7px;
  border-radius: var(--radius-full);
  background: var(--color-vu-amber-soft);
  font-size: 10px;
  font-weight: 500;
  color: var(--theme-warm);
}

/* ── 嵌入模式标题 ─────────────────────────────────── */
.vp-dock-head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.vp-dock-head__title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-ink);
}

.vp-dock-head__voice {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-size: 12px;
  color: var(--color-ink-muted);
}

/* ── 滑块容器 ─────────────────────────────────────── */
.vp-sliders { display: grid; gap: 20px; }
.vp-sliders--row { grid-template-columns: 1fr 1fr; gap: 16px; }
.vp-sliders--col { grid-template-columns: 1fr; }
.voice-params--compact .vp-sliders--row { gap: 14px; }

/* ── 单个参数字段 ─────────────────────────────────── */
.vp-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.vp-field__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.vp-field__label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-ink-muted);
}

.vp-field__value {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-ink);
}

.vp-field__value--text {
  font-family: var(--font-body);
  font-size: 13px;
}

.vp-field__tag {
  font-family: var(--font-body);
  font-size: 10px;
  font-weight: 400;
  padding: 1px 6px;
  border-radius: 3px;
  background: var(--color-vu-amber-soft);
  color: var(--theme-warm);
}

.vp-field__ticks {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--color-ink-faint);
  opacity: 0.5;
}

/* ── 滑条 ─────────────────────────────────────────── */
.vp-range {
  width: 100%;
  height: 5px;
  border-radius: var(--radius-full);
  background: linear-gradient(90deg, rgb(20 19 18 / 0.04), var(--color-vu-amber), rgb(20 19 18 / 0.04));
  appearance: none;
  cursor: pointer;
}

.vp-range::-webkit-slider-thumb {
  appearance: none;
  width: 16px;
  height: 16px;
  border: 2px solid #fff;
  border-radius: 50%;
  background: var(--color-vu-amber);
  box-shadow: 0 1px 3px rgb(44 40 36 / 0.15);
  cursor: pointer;
  transition: transform var(--duration-fast) var(--ease-out);
}

.vp-range::-webkit-slider-thumb:hover { transform: scale(1.15); }
.vp-range::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border: 2px solid #fff;
  border-radius: 50%;
  background: var(--color-vu-amber);
  box-shadow: 0 1px 3px rgb(44 40 36 / 0.15);
  cursor: pointer;
}

.vp-range:disabled { opacity: 0.3; cursor: not-allowed; }

/* ── 情感选择网格 ─────────────────────────────────── */
.vp-field--emotion { gap: 10px; }

.vp-emotion-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 5px;
}

.vp-emotion-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 7px 4px;
  border: 1px solid rgb(20 19 18 / 0.06);
  border-radius: var(--radius-ui);
  background: var(--color-surface);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.vp-emotion-btn:hover:not(:disabled) {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
}

.vp-emotion-btn--on {
  border-color: var(--color-vu-amber);
  background: linear-gradient(135deg, var(--color-vu-amber-soft), var(--color-vu-amber-dim));
  box-shadow: 0 0 0 2px var(--color-vu-amber-glow);
}

.vp-emotion-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.vp-emotion-btn__glyph {
  font-size: 14px;
  font-weight: 500;
  line-height: 1;
  color: var(--color-ink);
}

.vp-emotion-btn__text {
  font-size: 10px;
  font-weight: 500;
  color: var(--color-ink-muted);
}

.vp-emotion-btn--on .vp-emotion-btn__text { color: var(--theme-warm); }

/* ── 智能推荐区（去AI感，低调融入） ───────────────── */
.vp-reference {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--radius-module);
  background: var(--color-indigo-soft);
  border: 1px solid var(--color-indigo-mist);
}

.vp-ref-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 9px 12px;
  border: 1px solid var(--color-indigo-smoke);
  border-radius: var(--radius-ui);
  background: rgb(255 255 255 / 0.7);
  font-size: 12px;
  font-weight: 500;
  color: var(--color-indigo);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out);
}

.vp-ref-btn:hover:not(:disabled) {
  border-color: rgb(74 85 104 / 0.35);
  background: rgb(255 255 255 / 0.95);
  box-shadow: var(--shadow-glow-indigo);
  color: #2d3748;
}

.vp-ref-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.vp-ref-btn--loading { animation: breathe 2s ease-in-out infinite; }

@keyframes breathe {
  0%, 100% { opacity: 0.9; }
  50% { opacity: 0.5; }
}

.vp-ref-reason {
  padding: 8px 10px;
  border-radius: var(--radius-ui);
  background: var(--bg-surface-muted);
  border: 1px solid var(--color-indigo-mist);
}

.vp-ref-reason__text {
  margin: 0;
  font-size: 11px;
  font-style: italic;
  line-height: 1.6;
  color: var(--color-ink-muted);
}

.vp-ref-error {
  margin: 0;
  font-size: 11px;
  color: rgb(168 52 44 / 0.75);
}

.reason-fade-enter-active,
.reason-fade-leave-active {
  transition: all 0.3s var(--ease-out);
}

.reason-fade-enter-from,
.reason-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* ── 试听区 ───────────────────────────────────────── */
.vp-playback {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 16px;
  border-top: 1px solid var(--color-line);
}

.vp-playback__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.vp-playback__label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-ink-muted);
}

.vp-playback__export {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.04em;
  text-decoration: none;
  color: var(--color-ink-muted);
  padding: 3px 10px;
  border: 1px solid rgb(20 19 18 / 0.08);
  border-radius: var(--radius-full);
  transition: all var(--duration-fast) var(--ease-out);
}

.vp-playback__export:hover {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
  color: var(--theme-warm);
}

.vp-playback__player {
  border-radius: var(--radius-module);
  overflow: hidden;
  background: rgb(20 19 18 / 0.015);
  border: 1px solid var(--color-line);
}
</style>
