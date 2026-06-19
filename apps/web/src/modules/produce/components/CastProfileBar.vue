<script setup lang="ts">
import { ref, watch } from "vue";
import {
  createCastProfile,
  deleteCastProfile,
  downloadCastExport,
  getActiveCastProfile,
  importCastFromJson,
  listCastProfiles,
  switchCastProfile,
} from "@/modules/produce/utils/characterCast";

const props = defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{
  change: [];
}>();

const activeProfile = ref(getActiveCastProfile());
const profileNames = ref(listCastProfiles());
const newProfileName = ref("");
const showNewProfile = ref(false);
const importError = ref("");
const fileInputRef = ref<HTMLInputElement | null>(null);

function refreshProfiles() {
  profileNames.value = listCastProfiles();
  activeProfile.value = getActiveCastProfile();
}

watch(
  () => props.disabled,
  (busy) => {
    if (!busy) refreshProfiles();
  },
  { immediate: true },
);

function onSwitchProfile(name: string) {
  if (name === activeProfile.value) return;
  switchCastProfile(name);
  refreshProfiles();
  emit("change");
}

function onCreateProfile() {
  const name = newProfileName.value.trim();
  if (!name || !createCastProfile(name)) return;
  newProfileName.value = "";
  showNewProfile.value = false;
  refreshProfiles();
  emit("change");
}

function onDeleteProfile() {
  if (!deleteCastProfile(activeProfile.value)) return;
  refreshProfiles();
  emit("change");
}

function onExport() {
  downloadCastExport(activeProfile.value);
}

function onPickImport() {
  importError.value = "";
  fileInputRef.value?.click();
}

async function onImportFile(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  try {
    const raw: unknown = JSON.parse(await file.text());
    const result = importCastFromJson(raw);
    if (!result) {
      importError.value = "无法识别的卡司文件格式";
      return;
    }
    importError.value = "";
    refreshProfiles();
    emit("change");
  } catch {
    importError.value = "读取文件失败";
  } finally {
    input.value = "";
  }
}
</script>

<template>
  <section class="cast-profile-bar">
    <div class="cast-profile-bar__row">
      <label class="cast-profile-bar__label" for="cast-profile-select">项目卡司</label>
      <select
        id="cast-profile-select"
        class="cast-profile-bar__select"
        :value="activeProfile"
        :disabled="disabled"
        @change="onSwitchProfile(($event.target as HTMLSelectElement).value)"
      >
        <option v-for="name in profileNames" :key="name" :value="name">{{ name }}</option>
      </select>

      <button
        type="button"
        class="text-action"
        :disabled="disabled"
        @click="showNewProfile = !showNewProfile"
      >
        新建
      </button>
      <button
        type="button"
        class="text-action"
        :disabled="disabled || profileNames.length <= 1"
        @click="onDeleteProfile"
      >
        删除
      </button>
      <span class="cast-profile-bar__sep" aria-hidden="true">·</span>
      <button type="button" class="text-action" :disabled="disabled" @click="onExport">导出 JSON</button>
      <button type="button" class="text-action" :disabled="disabled" @click="onPickImport">导入 JSON</button>
      <input
        ref="fileInputRef"
        type="file"
        accept="application/json,.json"
        class="cast-profile-bar__file"
        @change="onImportFile"
      />
    </div>

    <div v-if="showNewProfile" class="cast-profile-bar__new">
      <input
        v-model="newProfileName"
        class="cast-profile-bar__input"
        type="text"
        maxlength="32"
        placeholder="例如：蛊真人第一集"
        :disabled="disabled"
        @keyup.enter="onCreateProfile"
      />
      <button type="button" class="btn btn--primary btn--sm" :disabled="disabled || !newProfileName.trim()" @click="onCreateProfile">
        创建
      </button>
      <button type="button" class="btn btn--ghost btn--sm" :disabled="disabled" @click="showNewProfile = false">
        取消
      </button>
    </div>

    <p v-if="importError" class="cast-profile-bar__error" role="alert">{{ importError }}</p>
    <p v-else class="cast-profile-bar__hint">按项目保存多套角色音色，可导出分享给团队或换机导入。</p>
  </section>
</template>

<style scoped>
.cast-profile-bar {
  margin-bottom: 14px;
  padding-bottom: 14px;
  border-bottom: 1px dashed rgb(212 205 195 / 0.85);
}

.cast-profile-bar__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 10px;
}

.cast-profile-bar__label {
  font-size: 12px;
  color: var(--color-ink-muted);
}

.cast-profile-bar__select {
  min-width: 140px;
  max-width: 220px;
  font-size: 13px;
}

.cast-profile-bar__sep {
  color: var(--color-ink-muted);
}

.cast-profile-bar__file {
  display: none;
}

.cast-profile-bar__new {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
}

.cast-profile-bar__input {
  flex: 1;
  min-width: 180px;
  font-size: 13px;
}

.cast-profile-bar__hint,
.cast-profile-bar__error {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-ink-muted);
}

.cast-profile-bar__error {
  color: var(--color-danger, #b42318);
}
</style>
