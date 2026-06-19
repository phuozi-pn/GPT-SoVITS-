<script setup lang="ts">
import { computed, ref, watch } from "vue";
import AppModal from "@/components/AppModal.vue";
import CastProfileBar from "@/modules/produce/components/CastProfileBar.vue";
import type { VoicePickerItem } from "@/components/VoicePicker.vue";
import {
  parseScreenplayScript,
  segmentsFromScreenplay,
  uniqueCharacters,
  type CharacterCast,
  type ScriptSegment,
} from "@/modules/produce/types/script";
import {
  rememberCastEntry,
  resolveCharacterCast,
  saveCharacterCast,
} from "@/modules/produce/utils/characterCast";

const props = defineProps<{
  open: boolean;
  voices: VoicePickerItem[];
  defaultVoiceId: string;
}>();

const emit = defineEmits<{
  close: [];
  apply: [segments: ScriptSegment[]];
}>();

const SAMPLE = `方源：你给我出来！
【白凝冰】你以为逃得掉吗？
旁白：夜色渐深，山谷里只剩下风声。
方源：今日之事，我记下了。`;

const raw = ref("");
const cast = ref<CharacterCast>({});

const parsed = computed(() => parseScreenplayScript(raw.value));
const characters = computed(() => uniqueCharacters(parsed.value));
const voiceIds = computed(() => props.voices.map((v) => v.id).filter(Boolean));

function reloadCast() {
  cast.value = resolveCharacterCast(characters.value, voiceIds.value);
}

watch(
  () => [props.open, characters.value.join("\0"), voiceIds.value.join("\0")] as const,
  ([visible]) => {
    if (!visible) return;
    reloadCast();
  },
);

watch(
  () => props.open,
  (visible) => {
    if (visible) return;
    raw.value = "";
  },
);

function loadSample() {
  raw.value = SAMPLE;
}

function onCastChange(name: string, voiceId: string) {
  cast.value = { ...cast.value, [name]: voiceId };
  rememberCastEntry(name, voiceId);
}

function onApply() {
  if (!parsed.value.length) return;
  const nextCast = resolveCharacterCast(characters.value, voiceIds.value, cast.value);
  saveCharacterCast(nextCast);
  const segments = segmentsFromScreenplay(parsed.value, nextCast, props.defaultVoiceId);
  emit("apply", segments);
  emit("close");
}
</script>

<template>
  <AppModal
    :open="open"
    label="情景配音"
    title="导入剧本"
    wide
    @close="emit('close')"
  >
    <CastProfileBar :disabled="false" @change="reloadCast" />

    <p class="import-hint">
      支持 <code>角色：台词</code>、<code>【角色】台词</code>、<code>(角色) 台词</code>、<code>角色|台词</code>。
      无角色前缀的行归入「旁白」。
    </p>

    <div class="import-actions">
      <button type="button" class="text-action" @click="loadSample">填入示例剧本</button>
      <span v-if="parsed.length" class="import-meta">
        已识别 <strong>{{ parsed.length }}</strong> 句 ·
        <strong>{{ characters.length }}</strong> 个角色
      </span>
    </div>

    <textarea
      v-model="raw"
      class="import-area"
      rows="10"
      spellcheck="false"
      placeholder="粘贴整段剧本，每行一句对白…"
    />

    <section v-if="characters.length" class="import-cast">
      <h3 class="rack-label">角色卡司</h3>
      <p class="import-cast-hint">为每个角色指定音色；变更会写入当前项目卡司。</p>
      <ul class="import-cast-list">
        <li v-for="name in characters" :key="name" class="import-cast-row">
          <span class="import-cast-name">{{ name }}</span>
          <select
            class="import-cast-voice"
            :value="cast[name] ?? defaultVoiceId"
            @change="onCastChange(name, ($event.target as HTMLSelectElement).value)"
          >
            <option v-for="v in voices" :key="v.id" :value="v.id">{{ v.title }}</option>
          </select>
        </li>
      </ul>
    </section>

    <template #footer>
      <button type="button" class="btn btn--ghost btn--sm" @click="emit('close')">取消</button>
      <button type="button" class="btn btn--primary btn--sm" :disabled="!parsed.length" @click="onApply">
        导入并分段
      </button>
    </template>
  </AppModal>
</template>

<style scoped>
.import-hint {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--color-ink-muted);
}

.import-hint code {
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--bg-tertiary);
}

.import-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 16px;
  margin-bottom: 10px;
}

.import-meta {
  font-size: 13px;
  color: var(--color-ink-muted);
}

.import-area {
  width: 100%;
  min-height: 200px;
  font-size: 15px;
  line-height: 1.65;
  resize: vertical;
}

.import-cast {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px dashed rgb(212 205 195 / 0.85);
}

.import-cast-hint {
  margin: 6px 0 12px;
  font-size: 13px;
  color: var(--color-ink-muted);
}

.import-cast-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.import-cast-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.import-cast-name {
  flex-shrink: 0;
  min-width: 72px;
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 14px;
}

.import-cast-voice {
  flex: 1;
  min-width: 0;
  font-size: 13px;
}
</style>
