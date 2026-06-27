<script setup lang="ts">
import { computed } from "vue";
import { avatarInitial, creatorAvatarUrl } from "@/utils/catalogDisplay";

const props = withDefaults(
  defineProps<{
    displayName: string;
    avatarUrl?: string | null;
    userId?: string | null;
    size?: "sm" | "md" | "lg";
    alt?: string;
  }>(),
  { size: "lg", alt: "", avatarUrl: null, userId: null },
);

const label = computed(() => props.alt || props.displayName || "创作者头像");
const initial = computed(() => avatarInitial(props.displayName));
const src = computed(() => creatorAvatarUrl(props.displayName, props.avatarUrl, props.userId));
</script>

<template>
  <div class="creator-avatar" :class="`creator-avatar--${size}`">
    <img
      v-if="src"
      class="creator-avatar__img"
      :src="src"
      :alt="label"
      loading="lazy"
      @error="($event.target as HTMLImageElement).hidden = true"
    />
    <span class="creator-avatar__fallback" aria-hidden="true">{{ initial }}</span>
  </div>
</template>

<style scoped>
.creator-avatar {
  position: relative;
  flex-shrink: 0;
  overflow: hidden;
  border-radius: 999px;
  background: linear-gradient(145deg, var(--theme-warm) 0%, var(--color-vu-amber-deep) 100%);
  box-shadow: 0 0 0 2px rgb(196 146 58 / 0.25);
}

.creator-avatar--sm {
  width: 38px;
  height: 38px;
}

.creator-avatar--md {
  width: 52px;
  height: 52px;
}

.creator-avatar--lg {
  width: 88px;
  height: 88px;
}

.creator-avatar__img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.creator-avatar__fallback {
  display: flex;
  width: 100%;
  height: 100%;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-weight: 600;
  color: #0a0b0d;
}

.creator-avatar--sm .creator-avatar__fallback {
  font-size: 1rem;
}

.creator-avatar--md .creator-avatar__fallback {
  font-size: 1.25rem;
}

.creator-avatar--lg .creator-avatar__fallback {
  font-size: 2rem;
}
</style>
