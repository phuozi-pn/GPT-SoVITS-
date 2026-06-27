<script setup lang="ts">
import { computed } from "vue";
import { creatorAvatarUrl } from "@/utils/catalogDisplay";

const props = withDefaults(
  defineProps<{
    name: string;
    avatarUrl?: string | null;
    userId?: string | null;
    size?: "sm" | "md" | "lg";
  }>(),
  { size: "md", avatarUrl: null, userId: null },
);

const initial = computed(() => {
  const t = props.name.trim();
  return t ? t.charAt(0) : "用";
});

const src = computed(() => creatorAvatarUrl(props.name, props.avatarUrl, props.userId));

const hue = computed(() => {
  let h = 0;
  for (let i = 0; i < props.name.length; i++) {
    h = (h + props.name.charCodeAt(i) * 17) % 360;
  }
  return h;
});
</script>

<template>
  <span
    class="user-avatar"
    :class="[`user-avatar--${size}`, { 'user-avatar--img': !!src }]"
    :style="src ? undefined : { background: `hsl(${hue} 45% 48%)` }"
    aria-hidden="true"
  >
    <img v-if="src" class="user-avatar__img" :src="src" :alt="name" loading="lazy" />
    <template v-else>{{ initial }}</template>
  </span>
</template>

<style scoped>
.user-avatar {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff;
  font-family: var(--font-display);
  font-weight: 600;
  line-height: 1;
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.2);
}

.user-avatar--sm {
  width: 32px;
  height: 32px;
  font-size: 13px;
}

.user-avatar--md {
  width: 40px;
  height: 40px;
  font-size: 15px;
}

.user-avatar--lg {
  width: 48px;
  height: 48px;
  font-size: 18px;
}

.user-avatar--img {
  overflow: hidden;
  padding: 0;
}

.user-avatar__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
