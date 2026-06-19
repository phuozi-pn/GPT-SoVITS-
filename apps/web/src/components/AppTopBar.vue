<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { getPageMeta, PUBLIC_SITE_ROUTE } from "@/config/navigation";

const route = useRoute();

const pageMeta = computed(() => getPageMeta(route.path, String(route.name ?? "")));
</script>

<template>
  <header class="app-topbar" :title="pageMeta.desc">
    <div class="app-topbar__lead">
      <p class="app-topbar__crumb">
        {{ pageMeta.group }} / <strong>{{ pageMeta.label }}</strong>
      </p>
      <p v-if="pageMeta.workflow" class="app-topbar__workflow">{{ pageMeta.workflow }}</p>
    </div>
    <div class="app-topbar__trail">
      <RouterLink :to="PUBLIC_SITE_ROUTE" class="text-action app-topbar__public">公开站点</RouterLink>
      <div v-if="$slots.actions" class="app-topbar__actions">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>
