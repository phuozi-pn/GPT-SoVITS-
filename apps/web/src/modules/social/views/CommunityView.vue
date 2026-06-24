<script setup lang="ts">
import { provide } from "vue";
import PageSurface from "@/components/PageSurface.vue";
import SocialSubNav from "@/modules/social/components/SocialSubNav.vue";
import CommunityInboxModals from "@/modules/social/components/CommunityInboxModals.vue";
import CommunityInboxPanel from "@/modules/social/components/CommunityInboxPanel.vue";
import { CommunityInboxKey, useCommunityInbox } from "@/modules/social/composables/useCommunityInbox";

const inbox = useCommunityInbox();
provide(CommunityInboxKey, inbox);

const {
  error,
} = inbox;
</script>

<template>
  <PageSurface class="page-surface--social">
    <SocialSubNav />
    <div v-if="error" class="alert alert--error social-body__alert">{{ error }}</div>

    <CommunityInboxPanel />
    <CommunityInboxModals />
  </PageSurface>
</template>

<style scoped>
.page-surface--social {
  flex: 1;
  min-height: 0;
}
.social-body__alert {
  margin: 0;
  border-radius: 0;
  border-top: 1px solid var(--surface-line, var(--border-glow));
}
</style>
