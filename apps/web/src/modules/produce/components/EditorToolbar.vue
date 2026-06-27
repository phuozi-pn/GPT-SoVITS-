<script setup lang="ts">
import type { ProduceWorkMode } from "@/modules/produce/types/script";

const props = withDefaults(
  defineProps<{
    disabled?: boolean;
    workMode?: ProduceWorkMode;
    compact?: boolean;
    segmenting?: boolean;
    llmEnabled?: boolean;
    polishing?: boolean;
    smartTuning?: boolean;
  }>(),
  { workMode: "single" },
);

const emit = defineEmits<{
  insertPause: [mark: string];
  clear: [];
  sample: [text: string];
  addSegment: [];
  importScript: [];
  smartSegment: [];
  smartTune: [];
  polishScript: [];
}>();

const pauseMarks = [
  { label: "半秒", mark: "……", hint: "0.5s" },
  { label: "整句", mark: "。", hint: "1s" },
  { label: "换行", mark: "\n\n", hint: "2s" },
] as const;

const samplesByMode: Record<ProduceWorkMode, string[]> = {
  single: ["你好，欢迎试听。", "今天我们来测试一下语音合成功能。"],
  dialogue: ["方源：你给我出来！\n白凝冰：你以为逃得掉吗？"],
  vocal: ["主唱：第一句歌词\n和声：和声歌词"],
};

function samplesFor(mode: ProduceWorkMode = "single") {
  return samplesByMode[mode] ?? samplesByMode.single;
}
</script>

<template>
  <div
    class="editor-toolbar"
    :class="{ 'editor-toolbar--compact': compact }"
    role="toolbar"
    aria-label="文稿工具"
  >
    <!-- ── 主操作行 ────────────────────────────────── -->
    <div class="tb-row tb-row--primary">
      <div class="tb-group">

        <span
          v-if="workMode"
          class="tb-mode-badge"
          :class="`tb-mode-badge--${workMode}`"
          role="status"
        >
          {{ workMode === "single" ? "单人朗读" : workMode === "dialogue" ? "多人情景" : "歌曲分段" }}
        </span>

        <!-- 清空 -->
        <button
          type="button"
          class="tb-btn tb-btn--quiet"
          :disabled="disabled"
          @click="emit('clear')"
        >
          清空
        </button>

        <span class="tb-sep" aria-hidden="true" />

        <button
          v-if="workMode !== 'single'"
          type="button"
          class="tb-btn tb-btn--dash"
          :class="{ 'tb-btn--pending': segmenting }"
          :disabled="disabled || segmenting"
          @click="emit('smartSegment')"
        >
          {{ segmenting ? "分析中…" : "智能分段" }}
        </button>

        <button
          v-if="workMode !== 'single'"
          type="button"
          class="tb-btn tb-btn--dash"
          :disabled="disabled"
          @click="emit('importScript')"
        >
          导入剧本
        </button>

        <button
          v-if="workMode !== 'single'"
          type="button"
          class="tb-btn tb-btn--dash"
          :disabled="disabled"
          @click="emit('addSegment')"
        >
          添加段落
        </button>
      </div>
    </div>

    <!-- 停顿（仅单人朗读，独立一行） -->
    <div v-if="workMode === 'single'" class="tb-row tb-row--pause">
      <span class="tb-label">停顿</span>
      <div class="tb-group">
        <button
          v-for="p in pauseMarks"
          :key="p.label"
          type="button"
          class="tb-btn tb-btn--tiny"
          :disabled="disabled"
          :title="`插入约 ${p.hint} 停顿`"
          @click="emit('insertPause', p.mark)"
        >
          {{ p.label }}
        </button>
      </div>
    </div>

    <!-- 智能表演 / 文稿润色 -->
    <div v-if="!compact && workMode !== 'single'" class="tb-muse-row">
      <div class="tb-muse-row__inner">
        <span class="tb-muse-row__tag" aria-hidden="true">灵感</span>
        <button
          type="button"
          class="tb-btn tb-btn--muse"
          :class="{ 'tb-btn--pending': smartTuning }"
          :disabled="disabled || smartTuning"
          :title="llmEnabled ? 'DeepSeek 逐段分析台词语义，推荐情感与韵律' : '规则分析台词语义，推荐情感与韵律（配置 DeepSeek 可更准确）'"
          @click="emit('smartTune')"
        >
          {{ smartTuning ? "分析中…" : "智能表演" }}
        </button>
        <button
          v-if="llmEnabled"
          type="button"
          class="tb-btn tb-btn--muse"
          :class="{ 'tb-btn--pending': polishing }"
          :disabled="disabled || polishing"
          @click="emit('polishScript')"
        >
          {{ polishing ? "润色中…" : "文稿润色" }}
        </button>
      </div>
    </div>

    <!-- ── 示例 ────────────────────────────────────── -->
    <div class="tb-samples">
      <span class="tb-label">示例</span>
      <button
        v-for="(s, i) in samplesFor(props.workMode)"
        :key="i"
        type="button"
        class="sample-chip"
        :disabled="disabled"
        @click="emit('sample', s)"
      >
        {{ s.length > 36 ? s.slice(0, 36) + "…" : s }}
      </button>
    </div>
  </div>
</template>

<style scoped>
/* ── 容器 ─────────────────────────────────────────── */
.editor-toolbar {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 18px;
  background: var(--color-xuan-light);
  border-bottom: 1px solid var(--color-line);
}

.editor-toolbar--compact {
  gap: 8px;
  padding: 10px 12px;
}

/* ── 行 ──────────────────────────────────────────── */
.tb-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
}

.tb-row--pause {
  padding: 10px 12px;
  border-radius: var(--radius-ui);
  background: rgb(20 19 18 / 0.03);
}

.tb-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.tb-sep {
  width: 1px;
  height: 16px;
  margin: 0 4px;
  background: var(--color-line-strong);
  flex-shrink: 0;
}

.tb-label {
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--color-ink-faint);
  margin-right: 2px;
  user-select: none;
}

/* ── 按钮基础 ────────────────────────────────────── */
.tb-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 7px 12px;
  min-height: 34px;
  border: 1px solid rgb(20 19 18 / 0.08);
  border-radius: var(--radius-full);
  background: var(--color-surface);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.35;
  color: var(--color-ink);
  cursor: pointer;
  white-space: nowrap;
  transition:
    border-color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out);
  user-select: none;
}

.tb-btn:hover:not(:disabled) {
  border-color: rgb(20 19 18 / 0.15);
  background: var(--color-xuan-warm);
}

.tb-btn:active:not(:disabled) {
  transform: scale(0.97);
}

.tb-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.tb-btn__glyph {
  font-size: 14px;
  line-height: 1;
  font-weight: 400;
}

/* 当前模式（只读，与页顶场景一致） */
.tb-mode-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.tb-mode-badge--single {
  background: rgb(59 130 246 / 0.12);
  color: var(--color-indigo-light);
}

.tb-mode-badge--dialogue {
  background: var(--color-vu-amber-soft);
  color: var(--theme-warm);
}

.tb-mode-badge--vocal {
  background: var(--color-indigo-soft);
  color: var(--color-indigo);
}

/* 变体：激活 */
.tb-btn--on {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
  color: var(--theme-warm);
  font-weight: 600;
}

/* 变体：静默 */
.tb-btn--quiet {
  border-color: transparent;
  background: transparent;
  color: var(--color-ink-muted);
}

.tb-btn--quiet:hover:not(:disabled) {
  border-color: rgb(20 19 18 / 0.06);
  background: rgb(20 19 18 / 0.02);
  color: var(--color-ink);
}

/* 变体：虚线 */
.tb-btn--dash {
  border-style: dashed;
  border-color: rgb(20 19 18 / 0.1);
  background: transparent;
}

.tb-btn--dash:hover:not(:disabled) {
  border-style: solid;
  border-color: rgb(20 19 18 / 0.15);
  background: var(--color-xuan-warm);
}

/* 变体：微小 */
.tb-btn--tiny {
  padding: 6px 12px;
  font-size: 12px;
  min-width: 44px;
  min-height: 34px;
}

/* ── 灵感行（替代原 AI 紫色区） ───────────────────── */
.tb-muse-row {
  display: flex;
  align-items: center;
}

.tb-muse-row__inner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: var(--radius-full);
  background: var(--color-indigo-soft);
  border: 1px solid var(--color-indigo-mist);
}

.tb-muse-row__tag {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--color-indigo);
  opacity: 0.65;
}

/* 灵感按钮 */
.tb-btn--muse {
  border-color: var(--color-indigo-smoke);
  background: var(--bg-surface-glass);
  color: var(--color-indigo);
  font-weight: 500;
  padding: 4px 11px;
  font-size: 11px;
}

.tb-btn--muse:hover:not(:disabled) {
  border-color: rgb(74 85 104 / 0.35);
  background: var(--bg-surface-raised);
  color: var(--color-indigo-light);
  box-shadow: var(--shadow-glow-indigo);
}

.tb-btn--muse.tb-btn--pending {
  animation: muse-breathe 2s ease-in-out infinite;
}

@keyframes muse-breathe {
  0%, 100% { opacity: 0.9; }
  50% { opacity: 0.55; }
}

/* ── 示例芯片 ─────────────────────────────────────── */
.tb-samples {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
  border-top: 1px solid rgb(212 205 195 / 0.35);
}

.sample-chip {
  max-width: 280px;
  padding: 6px 12px;
  border: 1px solid rgb(20 19 18 / 0.06);
  border-radius: var(--radius-full);
  background: var(--color-surface);
  font-size: 12px;
  line-height: 1.4;
  color: var(--color-ink-muted);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition:
    border-color var(--duration-fast) var(--ease-out),
    background var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out);
}

.sample-chip:hover:not(:disabled) {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
  color: var(--color-ink);
}

.sample-chip:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
</style>
