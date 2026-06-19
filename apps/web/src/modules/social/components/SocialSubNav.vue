<script setup lang="ts">
import { RouterLink, useRoute } from "vue-router";
import { SOCIAL_TABS } from "@/modules/social/constants";
import { useUnreadMessages } from "@/composables/useUnreadMessages";

const route = useRoute();
const { unreadTotal } = useUnreadMessages();
</script>

<template>
  <nav class="social-subnav" aria-label="社区子页面">
    <RouterLink
      v-for="tab in SOCIAL_TABS"
      :key="tab.to"
      :to="tab.to"
      class="social-subnav__item"
      :class="{ 'social-subnav__item--on': route.name === tab.name }"
    >
      {{ tab.label }}
      <span
        v-if="tab.name === 'community' && unreadTotal > 0"
        class="social-subnav__badge"
      >
        {{ unreadTotal > 99 ? "99+" : unreadTotal }}
      </span>
    </RouterLink>
  </nav>
</template>
