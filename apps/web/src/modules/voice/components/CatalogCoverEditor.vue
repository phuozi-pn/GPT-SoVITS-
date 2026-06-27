<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  generateCatalogCover,
  generateCatalogCoverForEntry,
  uploadCatalogCoverDraft,
  uploadCatalogCoverForEntry,
  updateCatalogEntry,
  type CatalogEntry,
} from "@/api/catalog";
import CatalogAvatar from "@/components/CatalogAvatar.vue";
import {
  DEFAULT_CATALOG_COVER_FEMALE,
  DEFAULT_CATALOG_COVER_MALE,
  defaultCatalogCoverForTags,
  normalizeCatalogTags,
  suggestCatalogCoverPrompt,
} from "@/utils/catalogDisplay";
import { formatApiError } from "@/utils/apiErrors";

const props = defineProps<{
  title: string;
  tags: string[];
  catalogId?: string;
  disabled?: boolean;
}>();

const coverUrl = defineModel<string>("coverUrl", { default: "" });

const emit = defineEmits<{
  entryUpdated: [entry: CatalogEntry];
}>();

type CoverMode = "ai" | "upload" | "default";

const mode = ref<CoverMode>("ai");
const coverPrompt = ref("");
const busy = ref(false);
const error = ref("");
const fileInput = ref<HTMLInputElement | null>(null);

const previewEntry = computed(() => ({
  catalog_id: props.catalogId ?? "preview",
  title: props.title || "预览",
  cover_image_url: coverUrl.value,
  tags: props.tags,
}));

watch(
  () => [props.title, props.tags] as const,
  () => {
    if (!coverPrompt.value.trim()) {
      coverPrompt.value = suggestCatalogCoverPrompt(props.title, props.tags);
    }
  },
  { immediate: true },
);

function fillPromptFromTags() {
  coverPrompt.value = suggestCatalogCoverPrompt(props.title, props.tags);
}

function applyDefaultCover(url: string) {
  void persistCoverUrl(url);
}

function useAutoDefault() {
  void persistCoverUrl(defaultCatalogCoverForTags(props.tags));
}

async function persistCoverUrl(url: string) {
  coverUrl.value = url;
  error.value = "";
  if (!props.catalogId) return;
  busy.value = true;
  try {
    const entry = await updateCatalogEntry(props.catalogId, { cover_image_url: url });
    coverUrl.value = entry.cover_image_url ?? url;
    emit("entryUpdated", entry);
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    busy.value = false;
  }
}

async function onGenerateAi() {
  error.value = "";
  const title = props.title.trim();
  if (!title) {
    error.value = "请先填写展示标题";
    return;
  }
  busy.value = true;
  try {
    const tags = normalizeCatalogTags(props.tags);
    const prompt = coverPrompt.value.trim() || undefined;
    if (props.catalogId) {
      const entry = await generateCatalogCoverForEntry(props.catalogId, { title, tags, prompt });
      coverUrl.value = entry.cover_image_url ?? coverUrl.value;
      emit("entryUpdated", entry);
    } else {
      const res = await generateCatalogCover({ title, tags, prompt });
      coverUrl.value = res.cover_image_url;
      if (res.prompt) coverPrompt.value = res.prompt;
    }
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    busy.value = false;
  }
}

function onPickUpload() {
  fileInput.value?.click();
}

async function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  if (!file.type.startsWith("image/")) {
    error.value = "请选择图片文件";
    return;
  }
  error.value = "";
  busy.value = true;
  try {
    if (props.catalogId) {
      const entry = await uploadCatalogCoverForEntry(props.catalogId, file);
      coverUrl.value = entry.cover_image_url ?? coverUrl.value;
      emit("entryUpdated", entry);
    } else {
      const res = await uploadCatalogCoverDraft(file);
      coverUrl.value = res.cover_image_url;
    }
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="cover-editor">
    <div class="cover-editor__preview">
      <CatalogAvatar :entry="previewEntry" size="lg" />
      <p class="hint cover-editor__preview-hint">全站展示预览（音色馆、创作者主页、首页精选）</p>
    </div>

    <div class="cover-editor__modes" role="tablist" aria-label="封面设置方式">
      <button
        type="button"
        class="cover-editor__mode"
        :class="{ 'cover-editor__mode--on': mode === 'ai' }"
        :disabled="disabled || busy"
        @click="mode = 'ai'"
      >
        AI 生成
      </button>
      <button
        type="button"
        class="cover-editor__mode"
        :class="{ 'cover-editor__mode--on': mode === 'upload' }"
        :disabled="disabled || busy"
        @click="mode = 'upload'"
      >
        上传图片
      </button>
      <button
        type="button"
        class="cover-editor__mode"
        :class="{ 'cover-editor__mode--on': mode === 'default' }"
        :disabled="disabled || busy"
        @click="mode = 'default'"
      >
        默认插画
      </button>
    </div>

    <div v-if="mode === 'ai'" class="cover-editor__panel">
      <label class="cover-editor__field">
        <span class="cover-editor__label">AI 绘图提示词</span>
        <textarea
          v-model="coverPrompt"
          rows="4"
          placeholder="描述角色气质、画风、背景…"
          :disabled="disabled || busy"
        />
      </label>
      <div class="cover-editor__actions">
        <button type="button" class="btn btn--ghost btn--sm" :disabled="disabled || busy" @click="fillPromptFromTags">
          从标签生成提示词
        </button>
        <button type="button" class="btn btn--primary btn--sm" :disabled="disabled || busy" @click="onGenerateAi">
          {{ busy ? "生成中…" : catalogId ? "生成并保存" : "生成封面" }}
        </button>
      </div>
      <p class="hint">通义万相生成，约 10–30 秒。{{ catalogId ? "保存后全站同步更新。" : "发布时将使用当前封面。" }}</p>
    </div>

    <div v-else-if="mode === 'upload'" class="cover-editor__panel">
      <input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" class="sr-only" @change="onFileChange" />
      <button
        type="button"
        class="cover-editor__upload-zone"
        :disabled="disabled || busy"
        @click="onPickUpload"
      >
        <span class="cover-editor__upload-title">{{ busy ? "上传中…" : "点击选择图片" }}</span>
        <span class="hint">PNG / JPG / WebP，最大 5MB</span>
      </button>
      <p class="hint">{{ catalogId ? "上传后立即保存并全站同步。" : "上传后将在发布时一并提交。" }}</p>
    </div>

    <div v-else class="cover-editor__panel">
      <div class="cover-editor__defaults">
        <button
          type="button"
          class="cover-editor__default-card"
          :disabled="disabled || busy"
          @click="applyDefaultCover(DEFAULT_CATALOG_COVER_MALE)"
        >
          <img :src="DEFAULT_CATALOG_COVER_MALE" alt="" width="72" height="72" />
          <span>男声默认</span>
        </button>
        <button
          type="button"
          class="cover-editor__default-card"
          :disabled="disabled || busy"
          @click="applyDefaultCover(DEFAULT_CATALOG_COVER_FEMALE)"
        >
          <img :src="DEFAULT_CATALOG_COVER_FEMALE" alt="" width="72" height="72" />
          <span>女声默认</span>
        </button>
        <button type="button" class="btn btn--ghost btn--sm" :disabled="disabled || busy" @click="useAutoDefault">
          按当前标签自动选择
        </button>
      </div>
      <p class="hint">使用平台内置插画，无需 AI 或上传。</p>
    </div>

    <p v-if="error" class="hint warn cover-editor__error">{{ error }}</p>
  </div>
</template>

<style scoped>
.cover-editor {
  display: grid;
  gap: 16px;
}

.cover-editor__preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  border-radius: var(--radius-ui);
  border: 1px solid rgb(196 146 58 / 0.18);
  background: var(--bg-surface-muted);
}

.cover-editor__preview-hint {
  margin: 0;
  text-align: center;
  font-size: 12px;
}

.cover-editor__modes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.cover-editor__mode {
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  font-size: 13px;
  cursor: pointer;
}

.cover-editor__mode--on {
  border-color: rgb(196 146 58 / 0.45);
  background: rgb(196 146 58 / 0.1);
  font-weight: 600;
}

.cover-editor__panel {
  display: grid;
  gap: 10px;
}

.cover-editor__field {
  display: grid;
  gap: 6px;
}

.cover-editor__label {
  font-size: 13px;
  font-weight: 600;
}

.cover-editor__field textarea {
  width: 100%;
  resize: vertical;
  min-height: 96px;
}

.cover-editor__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.cover-editor__upload-zone {
  display: grid;
  gap: 6px;
  justify-items: center;
  width: 100%;
  padding: 28px 16px;
  border: 2px dashed rgb(196 146 58 / 0.35);
  border-radius: var(--radius-ui);
  background: var(--bg-surface);
  cursor: pointer;
}

.cover-editor__upload-title {
  font-weight: 600;
}

.cover-editor__defaults {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.cover-editor__default-card {
  display: grid;
  gap: 6px;
  justify-items: center;
  padding: 10px 12px;
  border-radius: var(--radius-ui);
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  font-size: 12px;
  cursor: pointer;
}

.cover-editor__default-card img {
  border-radius: 12px;
}

.cover-editor__error {
  margin: 0;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}
</style>
