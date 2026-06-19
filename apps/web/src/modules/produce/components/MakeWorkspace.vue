<script setup lang="ts">
import type { VoicePickerItem } from "@/components/VoicePicker.vue";
import MakeActionBar from "@/modules/produce/components/MakeActionBar.vue";
import ScriptEditor from "@/modules/produce/components/ScriptEditor.vue";
import TapeReel from "@/modules/voice/components/studio/TapeReel.vue";
import { type ScriptSegment, type ProduceWorkMode } from "@/modules/produce/types/script";

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

const emit = defineEmits<{ generate: []; reload: [] }>();

const hasText = () => segments.value.some((s) => s.text.trim());
const isStudio = () => props.variant === "studio";
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
      <!-- 区域1: 音色选择（紧凑行） -->
      <div v-if="variant === 'full'" class="ws-voice-bar">
        <span class="ws-voice-bar__label">音色</span>
        <div class="ws-voice-bar__picker">
          <button
            v-for="v in voices"
            :key="v.id"
            type="button"
            class="voice-chip"
            :class="{ 'voice-chip--on': voiceId === v.id }"
            @click="voiceId = v.id"
          >
            <span class="voice-chip__avatar">{{ v.title.trim().charAt(0) || '音' }}</span>
            <span class="voice-chip__name">{{ v.title }}</span>
          </button>
        </div>
        <span class="ws-voice-bar__sep"></span>
        <div class="ws-voice-bar__tune">
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
            :compact="true"
          />
        </div>
      </div>

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
          :disabled="!hasText() || !voiceId"
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
  grid-template-columns: 1fr;
  grid-template-rows: 1fr auto;
}

/* ── 音色选择栏（紧凑行） ──────────────────────────── */
.ws-voice-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--color-line);
  background: var(--color-surface);
  overflow: hidden;
}

.ws-voice-bar__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-ink-muted);
  flex-shrink: 0;
}

.ws-voice-bar__picker {
  flex: 1;
  min-width: 0;
  display: flex;
  gap: 6px;
  overflow-x: auto;
  scrollbar-width: none;
}

.ws-voice-bar__picker::-webkit-scrollbar { display: none; }

.voice-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px 4px 6px;
  border: 1px solid rgb(212 205 195 / 0.3);
  border-radius: 8px;
  background: var(--bg-surface-muted);
  font-size: 12px;
  color: var(--color-ink-muted);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s;
  flex-shrink: 0;
}

.voice-chip:hover {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
  color: var(--color-ink);
}

.voice-chip--on {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
  color: var(--theme-warm);
  font-weight: 600;
}

.voice-chip__avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 5px;
  background: var(--color-vu-amber);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}

.voice-chip__name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ws-voice-bar__sep {
  width: 1px;
  height: 20px;
  background: rgb(212 205 195 / 0.3);
  flex-shrink: 0;
}

.ws-voice-bar__tune {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.ws-inline-param {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--color-ink-muted);
}

.ws-inline-param input[type="range"] {
  width: 80px;
  height: 4px;
  accent-color: var(--color-vu-amber);
  cursor: pointer;
}

.ws-inline-param__val {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--color-ink-faint);
  min-width: 32px;
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
