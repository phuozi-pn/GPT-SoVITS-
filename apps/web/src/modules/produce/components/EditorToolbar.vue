<script setup lang="ts">
defineProps<{
  disabled?: boolean;
  multiMode?: boolean;
  compact?: boolean;
  segmenting?: boolean;
  llmEnabled?: boolean;
  polishing?: boolean;
}>();

const emit = defineEmits<{
  insertPause: [mark: string];
  clear: [];
  sample: [text: string];
  toggleMulti: [];
  addSegment: [];
  importScript: [];
  smartSegment: [];
  polishScript: [];
}>();

const pauseMarks = [
  { label: "半秒", mark: "……", hint: "0.5s" },
  { label: "整句", mark: "。", hint: "1s" },
  { label: "换行", mark: "\n\n", hint: "2s" },
] as const;

const samples = [
  "你好，欢迎试听。",
  "方源：你给我出来！\n白凝冰：你以为逃得掉吗？",
  "今天我们来测试一下语音合成。",
];
</script>

<template>
  <div
    class="editor-toolbar"
    :class="{ 'editor-toolbar--compact': compact }"
    role="toolbar"
    aria-label="文稿工具"
  >
    <!-- ── 主操作行 ────────────────────────────────── -->
    <div class="tb-row">
      <div class="tb-group">

        <!-- 模式切换 -->
        <button
          type="button"
          class="tb-btn"
          :class="{ 'tb-btn--on': multiMode }"
          :disabled="disabled"
          @click="emit('toggleMulti')"
        >
          <span class="tb-btn__glyph" aria-hidden="true">☷</span>
          {{ multiMode ? "情景配音" : "单人朗读" }}
        </button>

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

        <!-- 导入 -->
        <button
          v-if="!compact"
          type="button"
          class="tb-btn tb-btn--dash"
          :disabled="disabled"
          @click="emit('importScript')"
        >
          导入剧本
        </button>

        <!-- 添加段落 -->
        <button
          v-if="multiMode && !compact"
          type="button"
          class="tb-btn tb-btn--dash"
          :disabled="disabled"
          @click="emit('addSegment')"
        >
          添加段落
        </button>
      </div>

      <!-- 停顿 -->
      <div class="tb-group">
        <span class="tb-label">停顿</span>
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

    <!-- ── 灵感辅助行（原 AI 区 → 人文化） ──────────── -->
    <div v-if="!compact" class="tb-muse-row">
      <div class="tb-muse-row__inner">
        <span class="tb-muse-row__tag" aria-hidden="true">灵感</span>
        <button
          type="button"
          class="tb-btn tb-btn--muse"
          :class="{ 'tb-btn--pending': segmenting }"
          :disabled="disabled || segmenting"
          @click="emit('smartSegment')"
        >
          {{ segmenting ? "分析中…" : "智能分段" }}
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
        v-for="(s, i) in samples"
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
  gap: 8px;
  padding: 10px 16px;
  background: var(--color-xuan-light);
  border-bottom: 1px solid var(--color-line);
}

.editor-toolbar--compact {
  gap: 6px;
  padding: 8px 12px;
}

/* ── 行 ──────────────────────────────────────────── */
.tb-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 6px 12px;
}

.tb-group {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
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
  padding: 5px 10px;
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

/* 变体：激活 */
.tb-btn--on {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
  color: #8a5a24;
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
  padding: 3px 8px;
  font-size: 11px;
  min-width: 32px;
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
  gap: 5px;
}

.sample-chip {
  max-width: 220px;
  padding: 4px 9px;
  border: 1px solid rgb(20 19 18 / 0.06);
  border-radius: var(--radius-full);
  background: var(--color-surface);
  font-size: 11px;
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
