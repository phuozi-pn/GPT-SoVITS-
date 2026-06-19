<script setup lang="ts">
import { computed, ref } from "vue";
export type VoicePickerItem = {
  id: string;
  title: string;
  subtitle?: string;
  tags?: string[];
  badge?: string;
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

    <button
      v-for="item in filtered"
      :key="item.id"
      type="button"
      class="vpicker__item"
      :class="{ 'vpicker__item--on': modelValue === item.id }"
      @click="emit('update:modelValue', item.id)"
    >
      <div class="vpicker__row">
        <div class="vpicker__avatar" aria-hidden="true">{{ avatar(item.title) }}</div>
        <div class="vpicker__copy">
          <div class="vpicker__head">
            <span class="vpicker__title">{{ item.title }}</span>
            <span v-if="item.badge" class="vpicker__badge">{{ item.badge }}</span>
          </div>
          <span v-if="item.subtitle" class="vpicker__sub">{{ item.subtitle }}</span>
          <div v-if="item.tags?.length" class="vpicker__tagline">
            <span v-for="t in item.tags.slice(0, 3)" :key="t" class="vpicker__tag">{{ t }}</span>
          </div>
        </div>
      </div>
    </button>
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
  display: block;
  width: 100%;
  margin: 0;
  padding: 12px 14px;
  border: none;
  border-bottom: 1px solid rgb(212 205 195 / 0.45);
  background: transparent;
  text-align: left;
  cursor: pointer;
  color: inherit;
  transition: background 0.18s ease;
}

.vpicker__item:hover {
  background: var(--bg-surface-glass);
}

.vpicker__item--on {
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
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--color-vu-amber-soft);
  font-size: 10px;
  color: #8a5a24;
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
