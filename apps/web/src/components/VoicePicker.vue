<script setup lang="ts">
import { computed, ref } from "vue";
import VoicePreviewButton from "@/components/VoicePreviewButton.vue";
import type { VoiceOriginKind } from "@/utils/voiceOriginDisplay";

export type VoicePickerItem = {
  id: string;
  title: string;
  subtitle?: string;
  tags?: string[];
  badge?: string;
  originKind?: VoiceOriginKind;
  synthReady?: boolean;
  previewAudioUrl?: string | null;
};

const props = defineProps<{
  items: VoicePickerItem[];
  modelValue: string;
  emptyText?: string;
}>();

const emit = defineEmits<{ "update:modelValue": [id: string] }>();

const query = ref("");
const activeTag = ref("");

const allTags = computed(() => {
  const set = new Set<string>();
  for (const item of props.items) {
    for (const t of item.tags ?? []) {
      if (t) set.add(t);
    }
  }
  return [...set].slice(0, 12);
});

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  return props.items.filter((item) => {
    if (activeTag.value && !(item.tags ?? []).includes(activeTag.value)) return false;
    if (!q) return true;
    return (
      item.title.toLowerCase().includes(q) ||
      item.subtitle?.toLowerCase().includes(q) ||
      item.tags?.some((t) => t.toLowerCase().includes(q))
    );
  });
});

function avatar(title: string): string {
  const t = title.trim();
  return t ? t.charAt(0) : "音";
}

function selectTag(tag: string) {
  activeTag.value = activeTag.value === tag ? "" : tag;
}
</script>

<template>
  <div class="vpicker">
    <header class="vpicker__head">选择音色</header>
    <div class="vpicker__search">
      <input v-model="query" type="search" placeholder="搜索主播或标签…" />
    </div>

    <div v-if="allTags.length" class="vpicker__tags">
      <button
        type="button"
        class="tag-chip"
        :class="{ 'tag-chip--active': !activeTag }"
        @click="activeTag = ''"
      >
        全部
      </button>
      <button
        v-for="t in allTags"
        :key="t"
        type="button"
        class="tag-chip"
        :class="{ 'tag-chip--active': activeTag === t }"
        @click="selectTag(t)"
      >
        {{ t }}
      </button>
    </div>

    <div v-if="!items.length" class="vpicker__empty">{{ emptyText }}</div>
    <div v-else-if="!filtered.length" class="vpicker__empty">没有匹配的音色——换个关键词或标签</div>

    <div
      v-for="item in filtered"
      :key="item.id"
      class="vpicker__item"
      :class="[
        { 'vpicker__item--on': modelValue === item.id },
        item.originKind ? `vpicker__item--${item.originKind}` : '',
      ]"
    >
      <VoicePreviewButton :src="item.previewAudioUrl" size="md" disabled-hint="—" />
      <button
        type="button"
        class="vpicker__select"
        @click="emit('update:modelValue', item.id)"
      >
        <div class="vpicker__row">
          <div class="vpicker__avatar" aria-hidden="true">{{ avatar(item.title) }}</div>
          <div class="vpicker__copy">
            <div class="vpicker__head">
              <span class="vpicker__title">{{ item.title }}</span>
              <span v-if="item.badge" class="vpicker__badge" :class="item.originKind ? `vpicker__badge--${item.originKind}` : ''">
                {{ item.badge }}
              </span>
            </div>
            <span v-if="item.subtitle" class="vpicker__sub">{{ item.subtitle }}</span>
            <div v-if="item.tags?.length" class="vpicker__tagline">
              <span v-for="t in item.tags.slice(0, 3)" :key="t" class="vpicker__tag">{{ t }}</span>
            </div>
          </div>
        </div>
      </button>
    </div>
  </div>
</template>

<style scoped>
.vpicker__head {
  margin: 0;
  padding: 14px 14px 0;
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
}

.vpicker__search {
  padding: 12px 14px;
  border-bottom: 1px solid rgb(212 205 195 / 0.65);
}

.vpicker__search input {
  font-size: 13px;
}

.vpicker__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px 14px;
  border-bottom: 1px solid rgb(212 205 195 / 0.65);
}

.vpicker__empty {
  padding: 32px 16px;
  text-align: center;
  font-size: 14px;
  color: var(--color-ink-muted);
}

.vpicker__item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  padding: 10px 12px;
  border: none;
  border-bottom: 1px solid rgb(212 205 195 / 0.45);
  border-left: 4px solid transparent;
  background: transparent;
  transition:
    background 0.18s ease,
    border-color 0.18s ease;
}

.vpicker__item--clone {
  border-left-color: var(--theme-warm);
  background: color-mix(in srgb, var(--theme-warm) 5%, transparent);
}

.vpicker__item--train {
  border-left-color: #5b8fd4;
  background: color-mix(in srgb, #5b8fd4 6%, transparent);
}

.vpicker__item--import {
  border-left-color: #9a8ec8;
  background: color-mix(in srgb, #9a8ec8 6%, transparent);
}

.vpicker__select {
  flex: 1;
  min-width: 0;
  margin: 0;
  padding: 2px 0 2px 4px;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  color: inherit;
}

.vpicker__item:hover {
  background: var(--bg-surface-glass);
}

.vpicker__item--on {
  box-shadow: inset 4px 0 0 currentColor;
}

.vpicker__item--on.vpicker__item--clone {
  background: color-mix(in srgb, var(--theme-warm) 16%, transparent);
  color: var(--theme-warm);
}

.vpicker__item--on.vpicker__item--train {
  background: color-mix(in srgb, #5b8fd4 14%, transparent);
}

.vpicker__item--on.vpicker__item--import {
  background: color-mix(in srgb, #9a8ec8 14%, transparent);
}

.vpicker__item--on:not([class*="vpicker__item--clone"]):not([class*="vpicker__item--train"]):not([class*="vpicker__item--import"]) {
  background: var(--color-vu-amber-soft);
  box-shadow: inset 3px 0 0 var(--color-vu-amber);
}

.vpicker__row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.vpicker__avatar {
  display: flex;
  height: 36px;
  width: 36px;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: linear-gradient(135deg, #c4923a 0%, #9a6a2a 100%);
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

.vpicker__copy {
  min-width: 0;
  flex: 1;
}

.vpicker__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.vpicker__title {
  font-size: 14px;
  font-weight: 600;
}

.vpicker__badge {
  flex-shrink: 0;
  padding: 3px 9px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.03em;
}

.vpicker__badge--clone {
  border-color: color-mix(in srgb, var(--theme-warm) 50%, transparent);
  background: color-mix(in srgb, var(--theme-warm) 18%, transparent);
  color: var(--theme-warm);
}

.vpicker__badge--train {
  border-color: color-mix(in srgb, #5b8fd4 50%, transparent);
  background: color-mix(in srgb, #5b8fd4 16%, transparent);
  color: #8eb8ea;
}

.vpicker__badge--import {
  border-color: color-mix(in srgb, #9a8ec8 45%, transparent);
  background: color-mix(in srgb, #9a8ec8 14%, transparent);
  color: #c4b8e8;
}

.vpicker__badge:not([class*="--"]) {
  background: var(--color-vu-amber-soft);
  color: var(--theme-warm);
}

.vpicker__sub {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: var(--color-ink-muted);
}

.vpicker__tagline {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.vpicker__tag {
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--bg-tertiary);
  font-size: 11px;
  color: var(--color-ink-muted);
}
</style>
