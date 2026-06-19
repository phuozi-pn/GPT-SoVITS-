<script setup lang="ts">
import { computed } from "vue";
import AppLayout from "@/components/AppLayout.vue";
import PublicLayout from "@/layouts/PublicLayout.vue";
import { useAppShell } from "@/composables/useAppShell";
import { useDocumentMeta } from "@/composables/useDocumentMeta";
import { useInkRipple } from "@/composables/useInkRipple";

const shell = useAppShell();
useDocumentMeta();
useInkRipple(); // 全局水墨涟漪 — 点击任意位置触发
const isBare = computed(() => shell.value === "bare");
const isPublic = computed(() => shell.value === "public");
</script>

<template>
  <!-- 全局装饰层 — 独立于路由切换，不随页面变化消失 -->
  <div class="deco-ambient" aria-hidden="true" />
  <div class="deco-ink-motes" aria-hidden="true" />
  <div class="deco-gold-dust" aria-hidden="true" />

  <router-view v-if="isBare" v-slot="{ Component, route: r }">
    <transition name="route-turn" mode="out-in">
      <component :is="Component" :key="r.path" />
    </transition>
  </router-view>

  <PublicLayout v-else-if="isPublic">
    <router-view v-slot="{ Component, route: r }">
      <transition name="route-turn" mode="out-in">
        <component :is="Component" :key="r.path" />
      </transition>
    </router-view>
  </PublicLayout>

  <AppLayout v-else>
    <router-view v-slot="{ Component, route: r }">
      <transition name="route-turn" mode="out-in">
        <component :is="Component" :key="r.path" />
      </transition>
    </router-view>
  </AppLayout>
</template>
