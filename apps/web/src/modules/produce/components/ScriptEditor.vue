<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import type { VoicePickerItem } from "@/components/VoicePicker.vue";
import { parseScriptSmart, fetchScriptParseStatus } from "@/api/script";
import { polishScript } from "@/api/intelligence";
import { ApiError } from "@/api/client";
import EditorToolbar from "@/modules/produce/components/EditorToolbar.vue";
import PartialAdjustBar from "@/modules/produce/components/PartialAdjustBar.vue";
import ScriptImportModal from "@/modules/produce/components/ScriptImportModal.vue";
import CastProfileBar from "@/modules/produce/components/CastProfileBar.vue";
import SegmentBlock from "@/modules/produce/components/SegmentBlock.vue";
import { newSegment, segmentCharCount, splitSegmentWithTune, autoSegmentText, autoSegmentLyrics, segmentsFromScreenplay, uniqueCharacters, type ProduceWorkMode, type ScreenplayLine, type ScriptSegment } from "@/modules/produce/types/script";
import { loadCharacterCast, rememberCastEntry, resolveCharacterCast } from "@/modules/produce/utils/characterCast";

const props = withDefaults(
  defineProps<{
    segments: ScriptSegment[];
    multiMode: boolean;
    workMode?: ProduceWorkMode;
    busy?: boolean;
    defaultVoiceId: string;
    voices: VoicePickerItem[];
    globalSpeed: number;
    globalTemperature: number;
    maxChars?: number;
    placeholder?: string;
    compact?: boolean;
  }>(),
  {
    maxChars: 10000,
    placeholder: "直接粘贴剧本或长文本。支持 角色：台词 自动识别角色并分配音色；纯文本按空行分段。",
  },
);

const editorPlaceholder = computed(() => {
  if (props.workMode === "vocal") {
    return "粘贴歌词，支持 主唱：歌词 / 和声：歌词 格式；[副歌] 等段落标记会被忽略。纯歌词按行分段。";
  }
  return props.placeholder;
});

const modeLabel = computed(() => {
  if (props.workMode === "vocal") return "歌曲分段 · 实验念唱";
  if (props.multiMode) return "情景配音";
  return "";
});

const emit = defineEmits<{
  "update:segments": [segments: ScriptSegment[]];
  "update:multiMode": [value: boolean];
}>();

const textareaRef = ref<HTMLTextAreaElement | null>(null);
const selectionStart = ref(0);
const selectionEnd = ref(0);
const localSpeed = ref(props.globalSpeed);
const localPitch = ref(1);
const activeSegmentId = ref<string | null>(null);
const showImportModal = ref(false);
const autoHint = ref("");
const segmenting = ref(false);
const polishing = ref(false);
const llmParseEnabled = ref(false);

const primary = computed({
  get: () => props.segments[0]?.text ?? "",
  set: (v: string) => {
    if (!props.segments[0]) return;
    const next = [...props.segments];
    next[0] = { ...next[0], text: v.slice(0, props.maxChars) };
    emit("update:segments", next);
  },
});

const charCount = computed(() => segmentCharCount(props.segments));
const selectionLength = computed(() => Math.abs(selectionEnd.value - selectionStart.value));

const estSeconds = computed(() => {
  const chars = props.segments.reduce((n, s) => n + s.text.trim().length, 0);
  if (!chars) return 0;
  return Math.max(1, Math.ceil(chars / (4 * props.globalSpeed)));
});

const hasContent = computed(() => charCount.value > 0);

watch(
  () => props.globalSpeed,
  (v) => { localSpeed.value = v; },
);

onMounted(async () => {
  try {
    const status = await fetchScriptParseStatus();
    llmParseEnabled.value = status.enabled;
  } catch {
    llmParseEnabled.value = false;
  }
});

function fmtDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function insertAtCursor(insert: string) {
  if (props.multiMode) return;
  const el = textareaRef.value;
  if (!el) {
    primary.value = primary.value + insert;
    return;
  }
  const start = el.selectionStart;
  const end = el.selectionEnd;
  const next = primary.value.slice(0, start) + insert + primary.value.slice(end);
  primary.value = next;
  requestAnimationFrame(() => {
    el.focus();
    const pos = start + insert.length;
    el.setSelectionRange(pos, pos);
  });
}

function onClear() {
  autoHint.value = "";
  if (props.multiMode) {
    emit("update:segments", [newSegment(props.defaultVoiceId)]);
    return;
  }
  primary.value = "";
  textareaRef.value?.focus();
}

function onSample(sample: string) {
  if (props.multiMode) {
    const seg = newSegment(props.defaultVoiceId, sample);
    emit("update:segments", [...props.segments, seg]);
    return;
  }
  primary.value = sample;
  textareaRef.value?.focus();
}

function trackSelection() {
  const el = textareaRef.value;
  if (!el) return;
  selectionStart.value = el.selectionStart;
  selectionEnd.value = el.selectionEnd;
  activeSegmentId.value = props.segments[0]?.id ?? null;
}

function applyPartialTune() {
  const segId = activeSegmentId.value ?? props.segments[0]?.id;
  if (!segId) return;
  const start = Math.min(selectionStart.value, selectionEnd.value);
  const end = Math.max(selectionStart.value, selectionEnd.value);
  const next = splitSegmentWithTune(props.segments, segId, start, end, {
    speed: localSpeed.value,
    pitch: localPitch.value,
  });
  emit("update:segments", next);
  if (next.length > 1) emit("update:multiMode", true);
}

function toggleMultiMode() {
  const next = !props.multiMode;
  if (next && props.segments.length === 1) {
    emit("update:multiMode", true);
    return;
  }
  if (!next) {
    const merged = props.segments.map((s) => s.text).join("");
    emit("update:segments", [newSegment(props.defaultVoiceId, merged)]);
  }
  emit("update:multiMode", next);
}

function addSegment() {
  emit("update:segments", [...props.segments, newSegment(props.defaultVoiceId)]);
  emit("update:multiMode", true);
}

function updateSegment(index: number, seg: ScriptSegment) {
  const next = [...props.segments];
  next[index] = seg;
  if (seg.characterName) {
    rememberCastEntry(seg.characterName, seg.voiceVersionId);
    for (let i = 0; i < next.length; i++) {
      if (i !== index && next[i].characterName === seg.characterName) {
        next[i] = { ...next[i], voiceVersionId: seg.voiceVersionId };
      }
    }
  }
  emit("update:segments", next);
}

function onImportApply(imported: ScriptSegment[]) {
  emit("update:segments", imported);
  emit("update:multiMode", true);
}

function applyCastToSegments() {
  const names = [...new Set(props.segments.map((s) => s.characterName).filter(Boolean) as string[])];
  if (!names.length) return;
  const voiceIds = props.voices.map((v) => v.id).filter(Boolean);
  const cast = resolveCharacterCast(names, voiceIds, loadCharacterCast());
  const next = props.segments.map((seg) => {
    if (!seg.characterName) return seg;
    const voiceVersionId = cast[seg.characterName] ?? seg.voiceVersionId;
    return voiceVersionId === seg.voiceVersionId ? seg : { ...seg, voiceVersionId };
  });
  emit("update:segments", next);
}

function onCastProfileChange() { applyCastToSegments(); }

function voiceIds() { return props.voices.map((v) => v.id).filter(Boolean); }

function applyLinesFromParse(lines: ScreenplayLine[], source: "llm" | "screenplay" | "paragraph") {
  const cast = resolveCharacterCast(uniqueCharacters(lines), voiceIds(), loadCharacterCast());
  const segments = segmentsFromScreenplay(lines, cast, props.defaultVoiceId);
  for (const seg of segments) {
    if (seg.characterName) rememberCastEntry(seg.characterName, seg.voiceVersionId);
  }
  emit("update:segments", segments);
  emit("update:multiMode", true);
  const chars = uniqueCharacters(lines);
  if (source === "llm") {
    autoHint.value = `已识别 ${lines.length} 句 · ${chars.length} 个角色，已自动分配音色`;
  } else if (source === "screenplay") {
    autoHint.value = `已识别 ${lines.length} 句 · ${chars.length} 个角色，已自动分配音色`;
  } else {
    autoHint.value = `已按 ${lines.length} 个段落自动分段并分配音色`;
  }
}

function applyAutoSegmentResult(raw: string): boolean {
  const result =
    props.workMode === "vocal"
      ? autoSegmentLyrics(raw, props.defaultVoiceId, voiceIds(), loadCharacterCast())
      : autoSegmentText(raw, props.defaultVoiceId, voiceIds(), loadCharacterCast());
  if (result.mode === "single") return false;
  if (result.mode === "screenplay" || result.mode === "lyrics") {
    const lines: ScreenplayLine[] = result.segments.map((s) => ({
      character: s.characterName ?? (props.workMode === "vocal" ? "主唱" : "旁白"),
      text: s.text,
    }));
    applyLinesFromParse(lines, result.mode === "lyrics" ? "paragraph" : "screenplay");
    if (result.mode === "lyrics") {
      autoHint.value = `已识别 ${result.lineCount} 行歌词 · ${result.characterCount} 个声部（实验性念唱）`;
    }
  } else {
    for (const seg of result.segments) {
      if (seg.characterName) rememberCastEntry(seg.characterName, seg.voiceVersionId);
    }
    emit("update:segments", result.segments);
    emit("update:multiMode", true);
    autoHint.value = `已按 ${result.lineCount} 个段落自动分段并分配音色`;
  }
  return true;
}

async function tryLLMSegment(text: string): Promise<boolean> {
  if (!llmParseEnabled.value) return false;
  try {
    const result = await parseScriptSmart(text);
    if (!result?.lines?.length) return false;
    applyLinesFromParse(result.lines, "llm");
    return true;
  } catch (err) {
    if (err instanceof ApiError) { autoHint.value = err.message; }
    return false;
  }
}

async function tryAutoSegment(raw?: string, opts?: { preferLlm?: boolean }) {
  if (props.multiMode || props.busy || segmenting.value) return false;
  const text = (raw ?? primary.value).trim();
  if (!text) return false;

  if (props.workMode === "vocal") {
    segmenting.value = true;
    try { return applyAutoSegmentResult(text); }
    finally { segmenting.value = false; }
  }

  const preferLlm = opts?.preferLlm ?? false;
  segmenting.value = true;
  try {
    if (preferLlm && llmParseEnabled.value) {
      if (await tryLLMSegment(text)) return true;
      if (applyAutoSegmentResult(text)) return true;
      autoHint.value = "未能自动分段，请检查文本或手动使用情景配音";
      return false;
    }
    if (applyAutoSegmentResult(text)) return true;
    if (llmParseEnabled.value && text.length >= 40) { return await tryLLMSegment(text); }
    return false;
  } finally { segmenting.value = false; }
}

async function onSmartSegment() {
  const ok = await tryAutoSegment(undefined, { preferLlm: props.workMode !== "vocal" });
  if (!ok && !autoHint.value) {
    autoHint.value =
      props.workMode === "vocal"
        ? "请使用 主唱：歌词 格式，或直接粘贴多行歌词"
        : llmParseEnabled.value
          ? "当前内容无需分段，或请使用 角色：台词 格式"
          : "规则分段未命中；可在服务端启用 DeepSeek 后使用智能分段";
  }
}

async function onPolishScript() {
  if (!llmParseEnabled.value || polishing.value) return;
  const text = props.multiMode
    ? props.segments.map((s) => s.characterName ? `${s.characterName}：${s.text}` : s.text).join("\n")
    : primary.value.trim();
  if (!text) { autoHint.value = "请先输入文本后再使用润色"; return; }
  polishing.value = true;
  autoHint.value = "";
  try {
    const result = await polishScript({ text, polish_scope: "full" });
    if (result.mode === "llm") {
      autoHint.value = `润色完成 — ${result.changes_summary}`;
      if (props.multiMode) {
        await tryAutoSegment(result.polished_text, { preferLlm: true });
      } else {
        primary.value = result.polished_text.slice(0, props.maxChars);
      }
    } else {
      autoHint.value = "润色服务暂不可用，请稍后重试";
    }
  } catch (err: unknown) {
    autoHint.value = err instanceof Error ? err.message : "润色失败，请稍后重试";
  } finally { polishing.value = false; }
}

function onPaste() {
  if (props.multiMode || props.busy) return;
  requestAnimationFrame(() => { void tryAutoSegment(); });
}

function onEditorBlur() {
  if (props.multiMode || props.busy || segmenting.value) return;
  applyAutoSegmentResult(primary.value.trim());
}

function removeSegment(index: number) {
  const next = props.segments.filter((_, i) => i !== index);
  emit("update:segments", next.length ? next : [newSegment(props.defaultVoiceId)]);
}
</script>

<template>
  <div class="script-editor" :class="{ 'script-editor--compact': compact }">
    <EditorToolbar
      :disabled="busy || segmenting"
      :multi-mode="multiMode"
      :compact="compact"
      :segmenting="segmenting"
      :polishing="polishing"
      :llm-enabled="llmParseEnabled"
      @insert-pause="insertAtCursor"
      @clear="onClear"
      @sample="onSample"
      @toggle-multi="toggleMultiMode"
      @add-segment="addSegment"
      @import-script="showImportModal = true"
      @smart-segment="onSmartSegment"
      @polish-script="onPolishScript"
    />

    <ScriptImportModal
      :open="showImportModal"
      :voices="voices"
      :default-voice-id="defaultVoiceId"
      @close="showImportModal = false"
      @apply="onImportApply"
    />

    <!-- 反馈提示条 -->
    <Transition name="hint-reveal">
      <div v-if="autoHint" class="editor-hint" role="status">
        <span class="editor-hint__mark" aria-hidden="true">—</span>
        {{ autoHint }}
        <button type="button" class="editor-hint__dismiss" @click="autoHint = ''" aria-label="关闭提示">&times;</button>
      </div>
    </Transition>

    <!-- 局部调节条 -->
    <PartialAdjustBar
      v-if="!multiMode"
      v-model:local-speed="localSpeed"
      v-model:local-pitch="localPitch"
      :selection-length="selectionLength"
      :disabled="busy || selectionLength === 0"
      @apply="applyPartialTune"
    />

    <!-- 主体编辑区 -->
    <div class="editor-body">
      <template v-if="multiMode">
        <div class="editor-body__cast">
          <CastProfileBar :disabled="busy" @change="onCastProfileChange" />
        </div>
        <div class="editor-body__segments">
          <SegmentBlock
            v-for="(seg, i) in segments"
            :key="seg.id"
            :segment="seg"
            :index="i"
            :voices="voices"
            :global-speed="globalSpeed"
            :global-temperature="globalTemperature"
            :disabled="busy"
            :can-remove="segments.length > 1"
            @update="updateSegment(i, $event)"
            @remove="removeSegment(i)"
          />
          <button type="button" class="seg-add" :disabled="busy" @click="addSegment">
            <span class="seg-add__plus" aria-hidden="true">+</span>
            {{ workMode === "vocal" ? "添加歌词段" : "添加对白段落" }}
          </button>
        </div>
      </template>

      <template v-else>
        <textarea
          ref="textareaRef"
          v-model="primary"
          class="editor-area"
          :placeholder="editorPlaceholder"
          :disabled="busy"
          spellcheck="false"
          @select="trackSelection"
          @keyup="trackSelection"
          @mouseup="trackSelection"
          @paste="onPaste"
          @blur="onEditorBlur"
        />
      </template>

      <!-- 空状态 -->
      <div v-if="!hasContent && !busy" class="editor-empty">
        <p class="editor-empty__title">开始书写</p>
        <p class="editor-empty__desc">
          粘贴剧本或输入文本，支持 <code>角色：台词</code> 格式<br />
          粘贴后自动识别角色，适合多人情景对话
        </p>
      </div>

      <!-- 忙碌 -->
      <div v-if="busy" class="editor-busy" aria-live="polite">
        <div class="editor-busy__ring" />
        <p class="editor-busy__label">正在生成</p>
        <p class="editor-busy__msg">文稿已锁定，请等待合成完成…</p>
      </div>
    </div>

    <!-- 底部信息栏 -->
    <footer class="editor-foot">
      <div class="editor-foot__left">
        <span class="editor-stat">{{ charCount }} / {{ maxChars }} 字</span>
        <span class="editor-stat__sep" aria-hidden="true" />
        <span class="editor-stat">约 {{ fmtDuration(estSeconds) }}</span>
      </div>
      <div class="editor-foot__right">
        <span v-if="multiMode" class="editor-chip">
          {{ segments.length }} 段 · 情景配音
        </span>
        <span v-if="llmParseEnabled" class="editor-chip editor-chip--soft">
          深度理解就绪
        </span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* ── 容器 ─────────────────────────────────────────── */
.script-editor {
  display: flex;
  min-height: 0;
  flex: 1;
  flex-direction: column;
  background: var(--color-surface);
}

/* ── 提示条 ──────────────────────────────────────── */
.editor-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 8px 16px;
  background: var(--color-warn-soft);
  border-bottom: 1px solid var(--color-warn-border);
  font-size: 12px;
  color: var(--theme-warm);
  line-height: 1.5;
}

.editor-hint__mark {
  flex-shrink: 0;
  font-weight: 300;
  color: var(--color-vu-amber);
  opacity: 0.7;
}

.editor-hint__dismiss {
  margin-left: auto;
  padding: 0 4px;
  border: none;
  background: none;
  font-size: 15px;
  line-height: 1;
  color: inherit;
  opacity: 0.4;
  cursor: pointer;
  transition: opacity var(--duration-fast);
}

.editor-hint__dismiss:hover { opacity: 0.8; }

.hint-reveal-enter-active,
.hint-reveal-leave-active {
  transition: all 0.3s var(--ease-out);
}

.hint-reveal-enter-from,
.hint-reveal-leave-to {
  opacity: 0;
  transform: translateY(-6px);
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

/* ── 主体 ─────────────────────────────────────────── */
.editor-body {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.script-editor--compact .editor-body {
  min-height: 0;
}

.editor-body__cast {
  padding: 16px 16px 0;
}

.editor-body__segments {
  padding: 10px 16px 16px;
}

/* 添加按钮 */
.seg-add {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  margin-top: 10px;
  padding: 12px;
  border: 1px dashed var(--border-glow);
  border-radius: var(--radius-module);
  background: transparent;
  font-size: 13px;
  color: var(--color-ink-muted);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out);
}

.seg-add:hover:not(:disabled) {
  border-color: var(--color-vu-amber);
  border-style: solid;
  background: var(--color-vu-amber-soft);
  color: #8a5a24;
}

.seg-add:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.seg-add__plus {
  font-size: 18px;
  font-weight: 200;
}

/* ── 文本域 ───────────────────────────────────────── */
.editor-area {
  display: block;
  width: 100%;
  min-height: 120px;
  height: 100%;
  resize: none;
  border: none;
  border-radius: 0;
  padding: 20px 28px 20px 68px;
  font-size: 16px;
  line-height: 1.9;
  letter-spacing: 0.01em;
  color: var(--color-ink);
  background:
    /* 行线 */
    repeating-linear-gradient(
      to bottom,
      transparent 0,
      transparent calc(1.9em - 1px),
      rgb(20 19 18 / 0.025) calc(1.9em - 1px),
      rgb(20 19 18 / 0.025) 1.9em
    ),
    /* 左栏标记 */
    linear-gradient(
      90deg,
      transparent 0,
      transparent 56px,
      rgb(196 146 58 / 0.06) 56px,
      rgb(196 146 58 / 0.06) 57px,
      transparent 57px
    ),
    var(--color-surface);
  transition: background var(--duration-slow) var(--ease-out);
  scrollbar-width: thin;
  scrollbar-color: rgb(212 205 195) transparent;
}

.script-editor--compact .editor-area {
  min-height: 80px;
  padding: 14px 20px 14px 48px;
  font-size: 14px;
  line-height: 1.65;
}

.editor-area::-webkit-scrollbar { width: 6px; }

.editor-area::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgb(212 205 195 / 0.85);
}

.editor-area:focus {
  outline: none;
  background:
    repeating-linear-gradient(
      to bottom,
      transparent 0,
      transparent calc(1.9em - 1px),
      rgb(20 19 18 / 0.035) calc(1.9em - 1px),
      rgb(20 19 18 / 0.035) 1.9em
    ),
    linear-gradient(
      90deg,
      transparent 0,
      transparent 56px,
      rgb(196 146 58 / 0.1) 56px,
      rgb(196 146 58 / 0.1) 57px,
      transparent 57px
    ),
    var(--bg-primary);
}

.editor-area::placeholder {
  color: var(--color-ink-faint);
  opacity: 0.5;
  font-style: italic;
}

/* ── 空状态 ───────────────────────────────────────── */
.editor-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
  pointer-events: none;
  user-select: none;
}

.editor-empty__title {
  margin: 0 0 12px;
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 400;
  color: var(--color-ink-muted);
  letter-spacing: 0.04em;
}

.editor-empty__desc {
  margin: 0;
  max-width: 380px;
  font-size: 13px;
  line-height: 1.8;
  color: var(--color-ink-faint);
}

.editor-empty__desc code {
  font-size: 0.9em;
  padding: 1px 6px;
  border-radius: 3px;
  background: rgb(20 19 18 / 0.05);
}

/* ── 忙碌状态 ─────────────────────────────────────── */
.editor-busy {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: var(--bg-surface-muted);
  backdrop-filter: blur(6px);
  pointer-events: none;
}

.editor-busy__ring {
  width: 28px;
  height: 28px;
  border: 2px solid rgb(196 146 58 / 0.15);
  border-top-color: var(--color-vu-amber);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.editor-busy__label {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-vu-amber-deep);
}

.editor-busy__msg {
  margin: 0;
  font-size: 13px;
  color: var(--color-ink-muted);
}

/* ── 底部信息栏 ──────────────────────────────────── */
.editor-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 16px 8px 68px;
  border-top: 1px solid var(--color-line);
  background: var(--color-surface-muted);
}

.editor-foot__left,
.editor-foot__right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.editor-stat {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.04em;
  color: var(--color-ink-muted);
}

.editor-stat__sep {
  width: 1px;
  height: 10px;
  background: var(--color-line-strong);
}

.editor-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: var(--color-vu-amber-soft);
  font-size: 10px;
  font-weight: 500;
  color: #8a5a24;
}

.editor-chip--soft {
  background: var(--color-indigo-soft);
  color: var(--color-indigo);
}
</style>
