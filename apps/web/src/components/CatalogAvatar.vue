<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { CatalogEntry } from "@/api/catalog";
import { avatarInitial, catalogAvatarUrl } from "@/utils/catalogDisplay";

const props = withDefaults(
  defineProps<{
    entry: Pick<CatalogEntry, "catalog_id" | "title" | "cover_image_url" | "tags">;
    size?: "sm" | "md" | "lg";
    alt?: string;
  }>(),
  { size: "lg", alt: "" },
);

const src = computed(() => catalogAvatarUrl(props.entry));
const label = computed(() => props.alt || props.entry.title || "音色封面");
const initial = computed(() => avatarInitial(props.entry.title));
const imgFailed = ref(false);

watch(src, () => {
  imgFailed.value = false;
});
</script>

<template>
  <div class="catalog-avatar" :class="`catalog-avatar--${size}`">
    <img
      v-if="src && !imgFailed"
      class="catalog-avatar__img"
      :src="src"
      :alt="label"
      loading="lazy"
      @error="imgFailed = true"
    />
    <span v-if="!src || imgFailed" class="catalog-avatar__fallback" aria-hidden="true">{{ initial }}</span>
  </div>
</template>

<style scoped>
.catalog-avatar {
  position: relative;
  flex-shrink: 0;
  overflow: hidden;
  border-radius: 18px;
  background: linear-gradient(145deg, var(--theme-warm) 0%, var(--color-vu-amber-deep) 100%);
  box-shadow:
    0 0 16px var(--theme-warm-glow),
    0 6px 18px rgb(0 0 0 / 0.12);
}

.catalog-avatar--sm {
  width: 40px;
  height: 40px;
  border-radius: 12px;
}

.catalog-avatar--md {
  width: 52px;
  height: 52px;
  border-radius: 14px;
}

.catalog-avatar--lg {
  width: 72px;
  height: 72px;
  border-radius: 18px;
}

.catalog-avatar__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.catalog-avatar__fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-size: 1.65rem;
  font-weight: 600;
  color: #0a0b0d;
}

.catalog-avatar--sm .catalog-avatar__fallback {
  font-size: 1rem;
}
</style>
