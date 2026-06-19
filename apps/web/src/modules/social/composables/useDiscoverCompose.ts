import { computed, ref } from "vue";
import { createCommunityPost } from "@/api/community";
import { formatApiError } from "@/utils/apiErrors";

const showCompose = ref(false);
const postBody = ref("");
const postTags = ref("");
const posting = ref(false);
const composeError = ref("");
const publishTick = ref(0);

const canPost = computed(() => postBody.value.trim().length > 0 && !posting.value);

function parseTags(raw: string): string[] {
  return raw
    .split(/[,，]/)
    .map((t) => t.trim())
    .filter(Boolean)
    .slice(0, 10);
}

function openCompose(prefill?: string) {
  if (prefill !== undefined) postBody.value = prefill;
}

function closeCompose() {
  showCompose.value = false;
  composeError.value = "";
}

async function submitPost(): Promise<boolean> {
  if (!canPost.value) return false;
  posting.value = true;
  composeError.value = "";
  try {
    await createCommunityPost({ body: postBody.value, tags: parseTags(postTags.value) });
    postBody.value = "";
    postTags.value = "";
    publishTick.value += 1;
    return true;
  } catch (e) {
    composeError.value = formatApiError(e);
    return false;
  } finally {
    posting.value = false;
  }
}

export function useDiscoverCompose() {
  return {
    showCompose,
    postBody,
    postTags,
    posting,
    composeError,
    canPost,
    publishTick,
    openCompose,
    closeCompose,
    submitPost,
  };
}
