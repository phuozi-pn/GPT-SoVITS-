<script setup lang="ts">
import { computed, ref } from "vue";
import type { VoicePickerItem } from "@/components/VoicePicker.vue";
import { recommendSynthParams } from "@/api/intelligence";
import MakeActionBar from "@/modules/produce/components/MakeActionBar.vue";
import ScriptEditor from "@/modules/produce/components/ScriptEditor.vue";
import RackPanel from "@/modules/voice/components/studio/RackPanel.vue";
import TapePlayer from "@/modules/voice/components/studio/TapePlayer.vue";
import TapeReel from "@/modules/voice/components/studio/TapeReel.vue";
import { validateSynthesisScript, type ScriptSegment, type ProduceWorkMode } from "@/modules/produce/types/script";
import {
  applySmartSynthToSegment,
  EMOTION_OPTIONS,
  formatSmartSynthHint,
} from "@/modules/produce/utils/smartSynth";

const props = withDefaults(
  defineProps<{
    voiceTitle?: string;
    voiceSubtitle?: string;
    voiceBadge?: string;
    voiceCount?: number;
    voices?: VoicePickerItem[];
    busy?: boolean;
    audioUrl?: string;
    exportHref?: string;
    generateLabel?: string;
    variant?: "full" | "studio";
    workMode?: ProduceWorkMode;
    title?: string;
    subtitle?: string;
  }>(),
  { variant: "full", voices: () => [], workMode: "single" },
);

const segments = defineModel<ScriptSegment[]>("segments", { required: true });
const multiMode = defineModel<boolean>("multiMode", { default: false });
const voiceId = defineModel<string>("voiceId", { required: true });
const aiAck = defineModel<boolean>("aiAck", { default: true });
const speed = defineModel<number>("speed", { default: 1.05 });
const temperature = defineModel<number>("temperature", { default: 0.78 });
const emotion = defineModel<string | null>("emotion", { default: null });
const emotionStrength = defineModel<number>("emotionStrength", { default: 0.5 });
const tunePending = defineModel<boolean>("tunePending", { default: false });

const emit = defineEmits<{ generate: []; reload: [] }>();

const hasText = () => segments.value.some((s) => s.text.trim());
const isStudio = () => props.variant === "studio";

const synthCheck = computed(() =>
  validateSynthesisScript(segments.value, {
    speed: speed.value,
    temperature: temperature.value,
    emotion: emotion.value,
    emotionStrength: emotionStrength.value,
  }),
);

const selectedVoice = computed(() => props.voices.find((v) => v.id === voiceId.value));

function voiceOptionLabel(v: VoicePickerItem): string {
  const parts = [v.title];
  if (v.badge) parts.push(v.badge);
  return parts.join(" · ");
}

const smartLoading = ref(false);
const smartHint = ref("");

const primaryText = computed(() => segments.value.find((s) => s.text.trim())?.text.trim() ?? "");

const emotionLabel = computed(() => {
  const hit = EMOTION_OPTIONS.find((o) => (o.value || null) === emotion.value);
  return hit?.label ?? "默认";
});

async function onSmartRecommend() {
  const text = primaryText.value;
  if (!text) {
    smartHint.value = "请先输入台词再使用智能推荐";
    return;
  }
  smartLoading.value = true;
  smartHint.value = "";
  try {
    const resp = await recommendSynthParams({ text });
    const result = resp.result;
    speed.value = result.speed_factor;
    temperature.value = result.temperature;
    emotion.value = result.emotion;
    emotionStrength.value = result.emotion_strength;

    const idx = segments.value.findIndex((s) => s.text.trim());
    if (idx >= 0) {
      const next = [...segments.value];
      next[idx] = applySmartSynthToSegment(next[idx], result);
      segments.value = next;
    }
    tunePending.value = true;
    smartHint.value = formatSmartSynthHint(result, resp.mode);
  } catch {
    smartHint.value = "智能推荐暂不可用，请检查 DeepSeek 配置或稍后重试";
  } finally {
    smartLoading.value = false;
  }
}
</script>

<template>
  <div class="workspace" :class="{ 'workspace--studio': isStudio() }">
    <!-- 顶部工具栏 -->
    <header v-if="variant === 'full'" class="ws-head">
      <div class="ws-head__left">
        <h2 class="ws-head__title">配音工作台</h2>
      </div>
      <div class="ws-head__right">
        <span class="ws-stat">
          <span class="ws-stat__num">{{ voiceCount ?? 0 }}</span> 个音色
        </span>
        <button type="button" class="ws-head__refresh" @click="emit('reload')">刷新</button>
      </div>
    </header>

    <!-- 主布局：上下结构 -->
    <div class="ws-grid" :class="{ 'ws-grid--workshop': !isStudio(), 'ws-grid--studio': isStudio() }">
      <!-- 区域1: 音色与全局参数 -->
      <div v-if="variant === 'full'" class="ws-voice-bar">
        <div class="ws-voice-bar__row">
          <span class="ws-voice-bar__label">音色</span>
          <div class="ws-voice-select-wrap">
            <select
              v-model="voiceId"
              class="ws-voice-select"
              :disabled="!voices.length"
            >
              <option v-if="!voices.length" value="" disabled>暂无可用音色</option>
              <option v-for="v in voices" :key="v.id" :value="v.id">
                {{ voiceOptionLabel(v) }}
              </option>
            </select>
            <p v-if="selectedVoice?.subtitle" class="ws-voice-select__meta">
              {{ selectedVoice.subtitle }}
            </p>
          </div>
        </div>
        <div class="ws-voice-bar__row ws-voice-bar__row--perform">
          <span class="ws-voice-bar__label">表演</span>
          <div class="ws-perform-wrap">
            <div class="ws-perform-main">
              <select
                v-model="emotion"
                class="ws-emotion-select"
                :disabled="busy"
              >
                <option :value="null">默认</option>
                <option value="neutral">中性</option>
                <option value="happy">喜悦</option>
                <option value="angry">愤怒</option>
                <option value="sad">哀伤</option>
                <option value="fearful">恐惧</option>
                <option value="calm">平静</option>
              </select>
              <button
                type="button"
                class="ws-smart-btn"
                :disabled="busy || smartLoading || !primaryText"
                :title="primaryText ? 'DeepSeek 语义分析台词，推荐情感与韵律' : '请先输入台词'"
                @click="onSmartRecommend"
              >
                {{ smartLoading ? "分析中…" : "智能推荐" }}
              </button>
              <span class="ws-perform-meta">{{ emotionLabel }} · 强度 {{ emotionStrength.toFixed(1) }}</span>
            </div>
            <p v-if="smartHint" class="ws-smart-hint">{{ smartHint }}</p>
            <details class="ws-advanced">
              <summary>高级韵律</summary>
              <div class="ws-voice-bar__tune ws-voice-bar__tune--nested">
                <label class="ws-inline-param">
                  <span>语速</span>
                  <input type="range" min="0.5" max="2" step="0.05" :value="speed" @input="speed = +($event.target as HTMLInputElement).value" />
                  <span class="ws-inline-param__val">{{ speed.toFixed(2) }}</span>
                </label>
                <label class="ws-inline-param">
                  <span>温度</span>
                  <input type="range" min="0.3" max="1.5" step="0.02" :value="temperature" @input="temperature = +($event.target as HTMLInputElement).value" />
                  <span class="ws-inline-param__val">{{ temperature.toFixed(2) }}</span>
                </label>
                <label class="ws-inline-param">
                  <span>强度</span>
                  <input type="range" min="0" max="1" step="0.05" :value="emotionStrength" @input="emotionStrength = +($event.target as HTMLInputElement).value" />
                  <span class="ws-inline-param__val">{{ emotionStrength.toFixed(2) }}</span>
                </label>
              </div>
            </details>
          </div>
        </div>
      </div>

      <!-- 区域2: 文稿编辑 -->
      <div class="ws-script">
        <div class="ws-script__body">
          <ScriptEditor
            v-model:segments="segments"
            v-model:multi-mode="multiMode"
            :work-mode="workMode"
            :busy="busy"
            :default-voice-id="voiceId"
            :voices="voices"
            :global-speed="speed"
            :global-temperature="temperature"
            :compact="isStudio()"
            @tune-pending="tunePending = $event"
          />
        </div>
      </div>

      <RackPanel
        v-if="isStudio() && (audioUrl || voiceId)"
        label="试听"
        title="合成结果"
        brushed
        body-class="ws-playback-body"
      >
        <TapePlayer v-if="audioUrl" :src="audioUrl" :height="56" theme="studio" compact />
        <p v-else class="ws-playback-pending hint">
          训练已完成。点击「开始合成」生成试听；云端首次合成需加载权重，约 2–4 分钟。
        </p>
        <div class="ws-playback-actions">
          <a v-if="exportHref" :href="exportHref" download class="ws-playback-dl">下载音频</a>
          <router-link to="/library" class="ws-playback-more">前往文本转语音继续创作</router-link>
        </div>
      </RackPanel>

      <section v-else-if="audioUrl" class="ws-playback">
        <div class="ws-playback__bar">
          <span class="ws-playback__label">合成试听</span>
          <a v-if="exportHref" :href="exportHref" download class="ws-playback__export">下载音频 ↓</a>
        </div>
        <TapePlayer :src="audioUrl" :height="48" />
      </section>

      <!-- 底部操作栏 -->
      <footer class="ws-foot">
        <Transition name="overlay-fade">
          <div v-if="busy" class="ws-busy" aria-hidden="true">
            <TapeReel :spinning="true" :size="48" />
            <p class="ws-busy__text">正在合成音频…</p>
          </div>
        </Transition>
        <MakeActionBar
          v-model:ai-ack="aiAck"
          :busy="busy"
          :disabled="!hasText() || !voiceId || !synthCheck.ok"
          :disabled-hint="!synthCheck.ok ? synthCheck.message : ''"
          :pending-tune="tunePending"
          :generate-label="generateLabel"
          :compact="isStudio()"
          @generate="emit('generate')"
        />
      </footer>
    </div>
  </div>
</template>

<style scoped>
/* ── 工作台容器 ──────────────────────────────────── */
.workspace {
  position: relative;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.workspace--studio {
  border: none;
  box-shadow: none;
  border-radius: 0;
  background: transparent;
}

/* ── 顶部工具栏 ──────────────────────────────────── */
.ws-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 20px;
  background: var(--color-xuan-light);
  border-bottom: 1px solid var(--color-line);
  flex-shrink: 0;
}

.ws-head__left { min-width: 0; }

.ws-head__title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  color: var(--color-ink);
}

.ws-head__right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.ws-stat {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: var(--color-vu-amber-soft);
  font-size: 11px;
  color: var(--theme-warm);
}

.ws-stat__num {
  font-family: var(--font-mono);
  font-weight: 700;
}

.ws-head__refresh {
  padding: 4px 10px;
  border: 1px solid var(--border-glow);
  border-radius: 6px;
  background: var(--bg-surface-glass);
  font-size: 11px;
  color: var(--color-ink-muted);
  cursor: pointer;
  transition: all 0.15s;
}

.ws-head__refresh:hover {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
  color: var(--theme-warm);
}

/* ── 网格布局 ──────────────────────────────────────── */
.ws-grid {
  display: grid;
  flex: 1;
  min-height: 0;
}

.ws-grid--workshop {
  grid-template-columns: 1fr;
  grid-template-rows: auto 1fr auto;
}

.ws-grid--studio {
  display: flex;
  flex-direction: column;
  grid-template-columns: unset;
  grid-template-rows: unset;
}

/* ── 音色与参数（两行布局） ─────────────────────────── */
.ws-voice-bar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-line);
  background: var(--color-surface);
}

.ws-voice-bar__row {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.ws-voice-bar__row--tune {
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid rgb(212 205 195 / 0.35);
}

.ws-voice-bar__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-ink-muted);
  flex-shrink: 0;
  width: 2.5em;
}

.ws-voice-select-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ws-voice-select {
  width: 100%;
  max-width: 360px;
  min-height: 36px;
  padding: 6px 32px 6px 12px;
  border: 1px solid rgb(212 205 195 / 0.45);
  border-radius: 10px;
  background: var(--bg-surface-muted);
  font-size: 13px;
  color: var(--color-ink);
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b6560' d='M2.5 4.5 6 8l3.5-3.5'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  transition: border-color 0.15s, background-color 0.15s;
}

.ws-voice-select:hover:not(:disabled) {
  border-color: var(--color-vu-amber);
  background-color: var(--color-vu-amber-soft);
}

.ws-voice-select:focus {
  outline: none;
  border-color: var(--color-vu-amber);
  box-shadow: 0 0 0 2px rgb(243 192 109 / 0.25);
}

.ws-voice-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.ws-voice-select__meta {
  margin: 0;
  font-size: 11px;
  color: var(--color-ink-muted);
  line-height: 1.4;
}

.ws-voice-bar__row--perform {
  align-items: flex-start;
  padding-top: 12px;
  border-top: 1px solid rgb(212 205 195 / 0.35);
}

.ws-perform-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ws-perform-main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 12px;
}

.ws-emotion-select {
  min-width: 96px;
  min-height: 34px;
  padding: 5px 28px 5px 10px;
  border: 1px solid rgb(212 205 195 / 0.45);
  border-radius: 10px;
  background: var(--bg-surface-muted);
  font-size: 13px;
  color: var(--color-ink);
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b6560' d='M2.5 4.5 6 8l3.5-3.5'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
}

.ws-smart-btn {
  padding: 6px 14px;
  border: 1px solid rgb(212 146 74 / 0.45);
  border-radius: 10px;
  background: var(--color-vu-amber-soft);
  font-size: 12px;
  font-weight: 600;
  color: #8a5a24;
  cursor: pointer;
  transition: border-color 0.15s, background-color 0.15s;
}

.ws-smart-btn:hover:not(:disabled) {
  border-color: var(--color-vu-amber);
  background: rgb(243 192 109 / 0.28);
}

.ws-smart-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.ws-perform-meta {
  font-size: 11px;
  color: var(--color-ink-muted);
}

.ws-smart-hint {
  margin: 0;
  font-size: 11px;
  line-height: 1.45;
  color: rgb(138 90 36 / 0.92);
}

.ws-advanced {
  font-size: 12px;
  color: var(--color-ink-muted);
}

.ws-advanced summary {
  cursor: pointer;
  user-select: none;
  list-style: none;
}

.ws-advanced summary::-webkit-details-marker {
  display: none;
}

.ws-voice-bar__tune--nested {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed rgb(212 205 195 / 0.35);
}

.ws-voice-bar__tune {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 20px 28px;
  flex: 1;
  min-width: 0;
}

.ws-inline-param {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--color-ink-muted);
  min-width: min(100%, 220px);
}

.ws-inline-param input[type="range"] {
  flex: 1;
  min-width: 100px;
  max-width: 160px;
  height: 6px;
  accent-color: var(--color-vu-amber);
  cursor: pointer;
}

.ws-inline-param__val {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--color-ink-faint);
  min-width: 36px;
  text-align: right;
}

/* ── 文稿区 ──────────────────────────────────────── */
.ws-script {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.ws-script__body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.ws-playback {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px 0;
  border-top: 1px solid var(--color-line);
}

.ws-playback__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ws-playback__label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-ink);
}

.ws-playback__export {
  font-size: 11px;
  text-decoration: none;
  color: var(--color-ink-muted);
  padding: 3px 10px;
  border: 1px solid rgb(20 19 18 / 0.08);
  border-radius: var(--radius-full);
}

.ws-playback__export:hover {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
  color: #8a5a24;
}

:deep(.ws-playback-body) {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ws-playback-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.75rem;
}

.ws-playback-more {
  font-size: 11px;
  color: var(--color-vu-amber, #c4923a);
  text-decoration: none;
}

.ws-playback-more:hover {
  text-decoration: underline;
}

.ws-playback-dl {
  align-self: flex-start;
  font-size: 11px;
  text-decoration: none;
  color: var(--color-ink-muted);
  padding: 4px 12px;
  border: 1px solid var(--border-glow, rgb(255 255 255 / 0.1));
  border-radius: var(--radius-full);
  transition: all 0.15s;
}

.ws-playback-dl:hover {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
  color: var(--theme-warm);
}

.ws-playback-pending {
  margin: 0;
  padding: 0.75rem 0.25rem;
  line-height: 1.5;
}

/* ── 底部操作栏 ────────────────────────────────────── */
.ws-foot {
  position: relative;
}

/* 合成中蒙层 */
.ws-busy {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: var(--bg-tertiary);
  backdrop-filter: blur(6px);
}

.ws-busy__text {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: var(--color-ink-muted);
}

.overlay-fade-enter-active,
.overlay-fade-leave-active {
  transition: opacity 0.35s var(--ease-out);
}

.overlay-fade-enter-from,
.overlay-fade-leave-to { opacity: 0; }
</style>
