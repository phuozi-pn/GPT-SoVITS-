<script setup lang="ts">
import { ref } from "vue";
import { useDiscoverCompose } from "@/modules/social/composables/useDiscoverCompose";

defineProps<{
  loading?: boolean;
}>();

const emit = defineEmits<{
  published: [];
  refresh: [];
}>();

const composeRef = ref<HTMLTextAreaElement | null>(null);
const { postBody, postTags, canPost, posting, composeError, submitPost } = useDiscoverCompose();

async function onPublish() {
  const ok = await submitPost();
  if (ok) emit("published");
}

defineExpose({
  focus: async () => {
    composeRef.value?.focus();
    composeRef.value?.scrollIntoView({ behavior: "smooth", block: "center" });
  },
});
</script>

<template>
  <section class="compose-card">
    <textarea
      ref="composeRef"
      v-model="postBody"
      class="compose-card__input"
      rows="3"
      maxlength="2000"
      placeholder="分享制作心得、授权问题、或音色使用技巧…"
    />
    <div v-if="composeError" class="alert alert--error compose-card__error">{{ composeError }}</div>
    <footer class="compose-card__foot">
      <input v-model="postTags" class="compose-card__tags" placeholder="标签（可选），如：短剧, 商用" />
      <div class="compose-card__actions">
        <button type="button" class="text-action" :disabled="loading" @click="emit('refresh')">刷新</button>
        <button type="button" class="btn btn--primary btn--sm" :disabled="!canPost" @click="onPublish">
          {{ posting ? "发布中…" : "发布" }}
        </button>
      </div>
    </footer>
  </section>
</template>
