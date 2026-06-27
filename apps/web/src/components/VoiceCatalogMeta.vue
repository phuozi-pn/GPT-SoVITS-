<script setup lang="ts">
import { computed } from "vue";
import type { CatalogEntry } from "@/api/catalog";
import {
  catalogOwnerLabel,
  displayVoiceGender,
  displayVoiceRoles,
  displayVoiceTraits,
  partitionVoiceTags,
  TAG_TIER_LIMITS,
} from "@/utils/catalogDisplay";

const props = withDefaults(
  defineProps<{
    entry: Pick<CatalogEntry, "tags" | "owner_user_id" | "owner_display_name" | "title" | "description">;
    showAuthor?: boolean;
    showTags?: boolean;
    showScenes?: boolean;
    tagLimit?: number;
    prominent?: boolean;
    tagsOnly?: boolean;
  }>(),
  {
    showAuthor: true,
    showTags: true,
    showScenes: undefined,
    tagLimit: 6,
    prominent: false,
    tagsOnly: false,
  },
);

const showSceneTags = computed(() => props.showScenes ?? !props.prominent);

const genderLabel = computed(() => displayVoiceGender(props.entry.tags ?? []));

const roleTags = computed(() => {
  const limit = props.prominent ? Math.min(props.tagLimit, 4) : Math.min(props.tagLimit, 3);
  return displayVoiceRoles(props.entry.tags ?? [], limit);
});

const traitTags = computed(() => {
  const limit = props.prominent ? TAG_TIER_LIMITS.traits : 3;
  return displayVoiceTraits(props.entry.tags ?? [], limit);
});

const sceneTags = computed(() => {
  if (!showSceneTags.value) return [];
  return partitionVoiceTags(props.entry.tags ?? []).scenes.slice(0, 2);
});

const hasCastInfo = computed(
  () => Boolean(genderLabel.value || roleTags.value.length || traitTags.value.length || sceneTags.value.length),
);
</script>

<template>
  <div
    v-if="showTags && hasCastInfo"
    class="voice-catalog-meta"
    :class="{
      'voice-catalog-meta--prominent': prominent,
      'voice-catalog-meta--tags-only': tagsOnly,
    }"
  >
    <div class="voice-cast-strip">
      <div v-if="genderLabel || roleTags.length" class="voice-cast-strip__row voice-cast-strip__row--roles">
        <span v-if="genderLabel" class="voice-cast-strip__gender">{{ genderLabel }}</span>
        <span
          v-for="role in roleTags"
          :key="role"
          class="voice-cast-strip__role"
        >
          {{ role }}
        </span>
      </div>
      <div v-if="traitTags.length" class="voice-cast-strip__row voice-cast-strip__row--traits">
        <span
          v-for="(trait, i) in traitTags"
          :key="trait"
          class="voice-cast-strip__trait"
        >
          <span v-if="i > 0" class="voice-cast-strip__sep" aria-hidden="true">/</span>
          {{ trait }}
        </span>
      </div>
      <div v-if="sceneTags.length && showSceneTags" class="voice-cast-strip__scenes">
        <span v-for="t in sceneTags" :key="t">{{ t }}</span>
      </div>
    </div>
  </div>

  <p
    v-if="showAuthor && !tagsOnly"
    class="voice-catalog-meta__author"
    :class="{ 'voice-catalog-meta__author--subtle': prominent }"
  >
    <router-link
      class="voice-catalog-meta__author-name"
      :to="`/creator/${entry.owner_user_id}`"
      @click.stop
    >
      {{ catalogOwnerLabel(entry) }}
    </router-link>
  </p>
</template>

<style scoped>
.voice-catalog-meta--prominent {
  margin-top: 2px;
}

.voice-catalog-meta--tags-only {
  margin: 0;
}

.voice-cast-strip {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgb(196 146 58 / 0.18);
  background: rgb(255 252 247 / 0.72);
}

.voice-catalog-meta--prominent .voice-cast-strip {
  padding: 14px 16px;
}

.voice-cast-strip__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.voice-cast-strip__row--roles + .voice-cast-strip__row--traits {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgb(196 146 58 / 0.12);
}

.voice-cast-strip__gender {
  padding: 4px 11px;
  border-radius: 6px;
  font-family: var(--font-scroll);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #4a3410;
  background: rgb(196 146 58 / 0.14);
}

.voice-catalog-meta--prominent .voice-cast-strip__gender {
  font-size: 14px;
  padding: 5px 12px;
}

.voice-cast-strip__role {
  font-family: var(--font-scroll);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--color-ink);
}

.voice-catalog-meta--prominent .voice-cast-strip__role {
  font-size: 15px;
}

.voice-cast-strip__role:not(:last-child)::after {
  content: "·";
  margin-left: 8px;
  color: rgb(196 146 58 / 0.45);
  font-weight: 400;
}

.voice-cast-strip__traits {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.voice-cast-strip__trait {
  font-size: 13px;
  letter-spacing: 0.14em;
  color: var(--color-vu-amber-deep);
}

.voice-catalog-meta--prominent .voice-cast-strip__trait {
  font-size: 14px;
}

.voice-cast-strip__sep {
  margin: 0 0.45em;
  color: rgb(196 146 58 / 0.35);
  font-weight: 300;
}

.voice-cast-strip__scenes {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  font-size: 11px;
  color: var(--color-ink-faint);
  letter-spacing: 0.06em;
}

.voice-catalog-meta__author {
  margin: 10px 0 0;
  font-size: 12px;
}

.voice-catalog-meta__author--subtle {
  margin-top: 8px;
}

.voice-catalog-meta__author-name {
  color: var(--color-ink-muted);
  text-decoration: none;
}

.voice-catalog-meta__author-name::before {
  content: "创作者 · ";
  color: var(--color-ink-faint);
}

.voice-catalog-meta__author-name:hover {
  color: var(--color-vu-amber-deep);
}
</style>
