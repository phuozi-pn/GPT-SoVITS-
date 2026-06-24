<script setup lang="ts">
import { onMounted } from "vue";
import { RouterLink } from "vue-router";
import { resumeStudioJobIfNeeded, useStudioJobBanner } from "@/modules/voice/composables/useStudioSession";

const { activeJob, showBanner, jobStatus } = useStudioJobBanner();

onMounted(() => {
  void resumeStudioJobIfNeeded();
});
</script>

<template>
  <div v-if="showBanner && activeJob" class="studio-job-banner" role="status">
    <span class="studio-job-banner__pulse" aria-hidden="true" />
    <span class="studio-job-banner__text">
      {{ activeJob.label }}
      <span class="studio-job-banner__status">· {{ jobStatus || "排队中" }}</span>
    </span>
    <RouterLink to="/studio" class="studio-job-banner__link">返回训练工作台</RouterLink>
  </div>
</template>

<style scoped>
.studio-job-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 16px;
  background: linear-gradient(90deg, rgb(196 146 58 / 0.18), rgb(196 146 58 / 0.08));
  border-bottom: 1px solid rgb(196 146 58 / 0.35);
  font-size: 0.9rem;
}

.studio-job-banner__pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-highlight, #c4923a);
  animation: studio-pulse 1.4s ease-in-out infinite;
}

@keyframes studio-pulse {
  0%,
  100% {
    opacity: 0.4;
    transform: scale(0.9);
  }
  50% {
    opacity: 1;
    transform: scale(1.1);
  }
}

.studio-job-banner__text {
  flex: 1;
  min-width: 0;
}

.studio-job-banner__status {
  opacity: 0.75;
}

.studio-job-banner__link {
  font-weight: 600;
  color: var(--color-highlight, #c4923a);
  text-decoration: none;
  white-space: nowrap;
}

.studio-job-banner__link:hover {
  text-decoration: underline;
}
</style>
