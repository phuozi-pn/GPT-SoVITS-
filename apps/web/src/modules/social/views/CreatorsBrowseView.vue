<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { fetchFeaturedCreators, type FeaturedCreatorSummary } from "@/api/public";
import CreatorAvatar from "@/components/CreatorAvatar.vue";
import CatalogAvatar from "@/components/CatalogAvatar.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import { formatApiError } from "@/utils/apiErrors";
import { creatorPublicPath } from "@/utils/catalogLinks";
import { hasAppSession } from "@/utils/session";
import { setPageMeta } from "@/utils/pageMeta";

const router = useRouter();
const loggedIn = computed(() => hasAppSession());
const loading = ref(true);
const error = ref("");
const creators = ref<FeaturedCreatorSummary[]>([]);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    creators.value = await fetchFeaturedCreators(48);
  } catch (e) {
    error.value = formatApiError(e);
    creators.value = [];
  } finally {
    loading.value = false;
  }
}

function goCreator(userId: string) {
  router.push(creatorPublicPath(userId));
}

onMounted(() => {
  setPageMeta("创作者 · Voice Studio", "浏览认证创作者与其公开音色代表作");
  void load();
});
</script>

<template>
  <div class="creators-browse">
    <header class="creators-browse__head">
      <h1 class="creators-browse__title">创作者</h1>
      <p class="creators-browse__lead">
        认证配音创作者与精选作品。点击卡片进入主页试听、洽谈授权。
      </p>
      <div class="creators-browse__toolbar">
        <button type="button" class="text-action" :disabled="loading" @click="load">刷新</button>
        <RouterLink v-if="loggedIn" to="/me" class="text-action text-action--accent">我的主页</RouterLink>
        <RouterLink v-else to="/login" class="text-action">登录后创建主页</RouterLink>
      </div>
    </header>

    <div v-if="error" class="alert alert--error">{{ error }}</div>
    <LoadingSpinner v-if="loading" inline text="加载创作者…" />

    <div v-else-if="!creators.length" class="empty-state">
      <p><strong>暂无公开创作者</strong></p>
      <p class="hint">音色馆上架后，创作者会出现在这里</p>
    </div>

    <ul v-else class="creators-browse__grid">
      <li v-for="c in creators" :key="c.user_id">
        <article class="creator-card">
          <button type="button" class="creator-card__main" @click="goCreator(c.user_id)">
            <CreatorAvatar
              :display-name="c.display_name"
              :avatar-url="c.avatar_url"
              :user-id="c.user_id"
              size="lg"
            />
            <div class="creator-card__meta">
              <h2 class="creator-card__name">{{ c.display_name }}</h2>
              <p class="creator-card__bio hint">{{ c.bio || "这位创作者还没有填写简介" }}</p>
              <p class="creator-card__stats hint">
                {{ c.published_count }} 作品 · {{ c.featured_voice_count }} 精选
              </p>
            </div>
          </button>
          <div v-if="c.spotlight_voice" class="creator-card__spotlight">
            <CatalogAvatar :entry="c.spotlight_voice" size="sm" />
            <div class="creator-card__spotlight-meta">
              <strong>{{ c.spotlight_voice.title }}</strong>
              <button type="button" class="text-action text-action--accent" @click="goCreator(c.user_id)">
                进入主页 →
              </button>
            </div>
          </div>
        </article>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.creators-browse {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 20px 48px;
}

.creators-browse__title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.75rem;
}

.creators-browse__lead {
  margin: 8px 0 0;
  color: var(--color-text-muted);
  max-width: 52ch;
}

.creators-browse__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 16px;
}

.creators-browse__grid {
  display: grid;
  gap: 16px;
  margin: 24px 0 0;
  padding: 0;
  list-style: none;
}

@media (min-width: 720px) {
  .creators-browse__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.creator-card {
  border: 1px solid var(--color-border);
  border-radius: 16px;
  background: var(--color-surface);
  overflow: hidden;
}

.creator-card__main {
  display: flex;
  gap: 16px;
  width: 100%;
  padding: 16px;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.creator-card__main:hover {
  background: rgb(196 146 58 / 0.06);
}

.creator-card__name {
  margin: 0;
  font-size: 1.1rem;
}

.creator-card__bio {
  margin: 6px 0 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.creator-card__stats {
  margin: 8px 0 0;
}

.creator-card__spotlight {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid var(--color-border);
  background: rgb(0 0 0 / 0.02);
}

.creator-card__spotlight-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
</style>
