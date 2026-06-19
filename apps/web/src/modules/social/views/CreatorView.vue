<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  fetchCatalogTags,
  fetchCreatorProfile,
  formatPriceCents,
  getDevUserId,
  type CatalogEntry,
  type CreatorProfile,
} from "@/api/catalog";
import {
  catalogDemoDownloadUrl,
  catalogVoicePackUrl,
  downloadCatalogAsset,
  updateMyProfile,
} from "@/api/social";
import AppModal from "@/components/AppModal.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import PageActionBar from "@/components/PageActionBar.vue";
import PageActionLink from "@/components/PageActionLink.vue";
import PageSurface from "@/components/PageSurface.vue";
import RackPanel from "@/modules/voice/components/studio/RackPanel.vue";
import TapePlayer from "@/modules/voice/components/studio/TapePlayer.vue";
import { formatApiError } from "@/utils/apiErrors";
import { catalogAppPath, loginToCatalogQuery } from "@/utils/catalogLinks";
import { useIsShowcaseVisitor } from "@/composables/useAppShell";
import { useCopyText } from "@/composables/useCopyText";
import { setPageMeta } from "@/utils/pageMeta";

const route = useRoute();
const router = useRouter();
const { copied: shareCopied, copy: copyShareLink } = useCopyText();
const profile = ref<CreatorProfile | null>(null);
const availableTags = ref<string[]>([]);
const selectedTags = ref<string[]>([]);
const tagQuery = ref("");
const loading = ref(false);
const error = ref("");
const success = ref("");
const editName = ref("");
const editBio = ref("");
const saving = ref(false);
const showEdit = ref(false);
const publicSelectedId = ref("");

const isShowcaseVisitor = useIsShowcaseVisitor();
const isSelf = computed(() => userId.value === getDevUserId());
const userId = computed(() => String(route.params.userId ?? ""));
const featuredVoices = computed(() => profile.value?.voices.filter((v) => v.featured) ?? []);
const otherVoices = computed(() => profile.value?.voices.filter((v) => !v.featured) ?? []);
const publicSelected = computed(() => otherVoices.value.find((e) => e.catalog_id === publicSelectedId.value));

function parseTags(raw: string): string[] {
  return raw
    .split(/[,，]/)
    .map((t) => t.trim())
    .filter(Boolean)
    .slice(0, 10);
}

function syncTagsToRoute() {
  const q = { ...route.query };
  if (selectedTags.value.length) {
    q.tags = selectedTags.value.join(",");
  } else {
    delete q.tags;
  }
  router.replace({ query: q });
}

function toggleTag(tag: string) {
  const idx = selectedTags.value.indexOf(tag);
  if (idx >= 0) {
    selectedTags.value.splice(idx, 1);
  } else {
    selectedTags.value.push(tag);
  }
  tagQuery.value = selectedTags.value.join(", ");
  syncTagsToRoute();
  void loadProfile();
}

function clearTagFilter() {
  selectedTags.value = [];
  tagQuery.value = "";
  syncTagsToRoute();
  void loadProfile();
}

async function applyTagQuery() {
  selectedTags.value = parseTags(tagQuery.value);
  syncTagsToRoute();
  await loadProfile();
}

function avatarInitial(title: string): string {
  return title.trim().charAt(0) || "音";
}

function goMessages(voiceTitle?: string) {
  const query: Record<string, string> = { peer: userId.value };
  if (voiceTitle) {
    query.draft = `你好，想咨询「${voiceTitle}」的授权与合作。`;
  }
  router.push({ path: "/community", query });
}

function goLoginMessage(voiceTitle?: string) {
  let redirect = `/community?peer=${encodeURIComponent(userId.value)}`;
  if (voiceTitle) {
    redirect += `&draft=${encodeURIComponent(`你好，想咨询「${voiceTitle}」的授权与合作。`)}`;
  }
  router.push({ path: "/login", query: { redirect } });
}

function contactCreator(voiceTitle?: string) {
  if (isShowcaseVisitor.value) goLoginMessage(voiceTitle);
  else goMessages(voiceTitle);
}

function goCatalog(entry: CatalogEntry) {
  if (isShowcaseVisitor.value) {
    router.push({ path: "/browse", query: { pick: entry.catalog_id } });
    return;
  }
  router.push(catalogAppPath(entry.catalog_id));
}

function goCatalogHub() {
  if (isShowcaseVisitor.value) router.push("/browse");
  else router.push("/catalog");
}

function goLoginForCatalog(entry?: CatalogEntry) {
  router.push({ path: "/login", query: loginToCatalogQuery(entry?.catalog_id) });
}

function selectPublicVoice(id: string) {
  publicSelectedId.value = id;
}

function shareCreatorPage() {
  void copyShareLink(window.location.href);
}

async function onSaveProfile() {
  saving.value = true;
  error.value = "";
  success.value = "";
  try {
    await updateMyProfile({ display_name: editName.value.trim(), bio: editBio.value.trim() });
    success.value = "主页已更新";
    showEdit.value = false;
    await loadProfile();
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    saving.value = false;
  }
}

function openEdit() {
  if (profile.value) {
    editName.value = profile.value.display_name;
    editBio.value = profile.value.bio ?? "";
  }
  showEdit.value = true;
}

async function onDownloadDemo(entry: CatalogEntry) {
  try {
    await downloadCatalogAsset(catalogDemoDownloadUrl(entry.catalog_id), `${entry.title}_demo.wav`);
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}

async function onDownloadPack(entry: CatalogEntry) {
  try {
    await downloadCatalogAsset(catalogVoicePackUrl(entry.catalog_id), `${entry.title}_pack.zip`);
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}

async function loadProfile() {
  if (!userId.value) return;
  loading.value = true;
  error.value = "";
  try {
    profile.value = await fetchCreatorProfile(userId.value, {
      tags: selectedTags.value.length ? selectedTags.value : undefined,
    });
    if (isSelf.value && profile.value) {
      editName.value = profile.value.display_name;
      editBio.value = profile.value.bio ?? "";
    }
    const others = profile.value?.voices.filter((v) => !v.featured) ?? [];
    if (others.length && !others.some((e) => e.catalog_id === publicSelectedId.value)) {
      publicSelectedId.value = others[0].catalog_id;
    }
  } catch (e) {
    error.value = formatApiError(e);
    profile.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  const fromQuery = parseTags(String(route.query.tags ?? ""));
  if (fromQuery.length) {
    selectedTags.value = fromQuery;
    tagQuery.value = fromQuery.join(", ");
  }
  try {
    availableTags.value = await fetchCatalogTags();
  } catch {
    availableTags.value = [];
  }
  await loadProfile();
});

watch(
  () => route.params.userId,
  () => {
    void loadProfile();
  },
);

watch(
  () => profile.value,
  (p) => {
    if (!p || !isShowcaseVisitor.value) return;
    const title = `${p.display_name} · 创作者 · Voice Studio`;
    const desc =
      p.bio?.trim() ||
      `公开音色 ${p.published_count} 个 · 在 Voice Studio 浏览授权与试听样音`;
    setPageMeta(title, desc);
  },
);
</script>

<template>
  <!-- 访客展示壳 -->
  <div v-if="isShowcaseVisitor" class="showcase-creator">
    <div v-if="error" class="alert alert--error">{{ error }}</div>

    <p v-if="loading && !profile" class="hint">加载创作者主页…</p>

    <div v-if="profile" class="creator-profile-hero creator-profile-hero--showcase">
      <div class="creator-profile-hero__avatar" aria-hidden="true">
        {{ avatarInitial(profile.display_name) }}
      </div>
      <div class="creator-profile-hero__copy">
        <p class="showcase-creator__eyebrow">创作者</p>
        <h1 class="creator-profile-hero__name">{{ profile.display_name }}</h1>
        <p class="creator-profile-hero__bio">{{ profile.bio || "这位创作者还没有填写简介" }}</p>
        <p class="showcase-creator__stats hint">
          公开音色 <strong>{{ profile.published_count }}</strong>
          <template v-if="featuredVoices.length">
            · 精选 <strong>{{ featuredVoices.length }}</strong>
          </template>
        </p>
      </div>
      <div class="creator-profile-hero__actions row-actions">
        <button type="button" class="text-action" @click="shareCreatorPage">
          {{ shareCopied ? "已复制链接" : "分享主页" }}
        </button>
        <span class="row-actions__sep" aria-hidden="true">·</span>
        <button type="button" class="text-action" @click="goCatalogHub">音色馆</button>
        <span class="row-actions__sep" aria-hidden="true">·</span>
        <button type="button" class="text-action text-action--accent" @click="contactCreator()">登录后私信</button>
      </div>
    </div>

    <section v-if="profile" class="showcase-section">
      <h2 class="showcase-section__title">公开作品</h2>

      <div class="showcase-browse__toolbar">
        <input
          v-model="tagQuery"
          placeholder="按标签筛选，如：短剧, 男声"
          @keyup.enter="applyTagQuery"
        />
        <button type="button" class="btn btn--primary btn--sm" :disabled="loading" @click="applyTagQuery">搜索</button>
        <button v-if="selectedTags.length" type="button" class="text-action" :disabled="loading" @click="clearTagFilter">
          清除
        </button>
      </div>

      <div v-if="availableTags.length" class="tag-chips" style="margin-bottom: 16px">
        <button
          v-for="t in availableTags.slice(0, 12)"
          :key="t"
          type="button"
          class="tag-chip"
          :class="{ 'tag-chip--active': selectedTags.includes(t) }"
          @click="toggleTag(t)"
        >
          {{ t }}
        </button>
      </div>

      <div v-if="featuredVoices.length" class="showcase-creator__featured">
        <article v-for="e in featuredVoices" :key="e.catalog_id" class="showcase-creator__featured-card">
          <div class="showcase-creator__featured-head">
            <span class="showcase-case__tag">精选</span>
            <h3 class="showcase-preview__title">{{ e.title }}</h3>
            <p class="hint">{{ e.description || e.voice_name }}</p>
          </div>
          <TapePlayer v-if="e.demo_audio_url" :src="e.demo_audio_url" :height="72" />
          <p v-else class="hint">暂无样音</p>
          <div class="row-actions showcase-creator__featured-actions">
            <button type="button" class="text-action text-action--accent" @click="goCatalog(e)">试听详情 →</button>
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <button type="button" class="text-action" @click="contactCreator(e.title)">咨询授权</button>
          </div>
        </article>
      </div>

      <div v-if="otherVoices.length" class="showcase-browse__layout" style="margin-top: 8px">
        <ul class="showcase-browse__list">
          <li v-for="e in otherVoices" :key="e.catalog_id">
            <button
              type="button"
              class="showcase-voice-tile"
              :class="{ 'showcase-voice-tile--on': publicSelectedId === e.catalog_id }"
              @click="selectPublicVoice(e.catalog_id)"
            >
              <span class="showcase-voice-tile__avatar" aria-hidden="true">{{ avatarInitial(e.title) }}</span>
              <span class="showcase-voice-tile__meta">
                <strong>{{ e.title }}</strong>
                <span class="hint">{{ formatPriceCents(e.price_cents) }}</span>
              </span>
            </button>
          </li>
        </ul>

        <aside v-if="publicSelected" class="showcase-browse__detail">
          <h3 class="showcase-preview__title">{{ publicSelected.title }}</h3>
          <p class="hint">{{ publicSelected.description || publicSelected.voice_name }}</p>
          <TapePlayer v-if="publicSelected.demo_audio_url" :src="publicSelected.demo_audio_url" :height="88" />
          <p v-else class="hint">暂无样音</p>
          <p class="hint" style="margin-top: 12px">{{ formatPriceCents(publicSelected.price_cents) }}</p>
          <div class="showcase-browse__detail-actions">
            <button type="button" class="btn btn--primary btn--sm" @click="goLoginForCatalog(publicSelected)">
              登录后购买 / 合成
            </button>
            <span class="row-actions" style="margin-left: 12px">
              <button type="button" class="text-action text-action--accent" @click="contactCreator(publicSelected.title)">
                咨询
              </button>
            </span>
          </div>
        </aside>
      </div>

      <div v-if="!profile.voices.length && !loading" class="empty-state">
        <p><strong>暂无符合筛选的公开音色</strong></p>
      </div>
    </section>
  </div>

  <!-- 工作台内 -->
  <div v-else class="page page--full creator-page">
    <div v-if="error" class="alert alert--error">{{ error }}</div>
    <div v-if="success" class="alert alert--ok">{{ success }}</div>

    <PageSurface>
      <div v-if="profile" class="creator-profile-hero">
      <div class="creator-profile-hero__avatar" aria-hidden="true">
        {{ avatarInitial(profile.display_name) }}
      </div>
      <div class="creator-profile-hero__copy">
        <h1 class="creator-profile-hero__name">{{ profile.display_name }}</h1>
        <p class="creator-profile-hero__bio">{{ profile.bio || "这位创作者还没有填写简介" }}</p>
        <p class="showcase-creator__stats hint">
          公开音色 <strong>{{ profile.published_count }}</strong>
          <template v-if="featuredVoices.length">
            · 精选 <strong>{{ featuredVoices.length }}</strong>
          </template>
        </p>
      </div>
      <div class="creator-profile-hero__actions row-actions">
        <button type="button" class="text-action" @click="shareCreatorPage">
          {{ shareCopied ? "已复制链接" : "分享主页" }}
        </button>
        <span class="row-actions__sep" aria-hidden="true">·</span>
        <router-link to="/catalog" class="text-action">音色馆</router-link>
        <span class="row-actions__sep" aria-hidden="true">·</span>
        <router-link to="/community" class="text-action">消息</router-link>
        <template v-if="isSelf">
          <span class="row-actions__sep" aria-hidden="true">·</span>
          <button type="button" class="text-action" @click="openEdit">编辑主页</button>
        </template>
        <template v-else>
          <span class="row-actions__sep" aria-hidden="true">·</span>
          <button type="button" class="text-action text-action--accent" @click="goMessages()">发私信</button>
        </template>
      </div>
      </div>
      <p v-else-if="loading" class="hint" style="padding: 8px 0">加载创作者主页…</p>

      <RackPanel label="作品" title="公开音色">
      <div class="catalog-toolbar">
        <div class="filter-bar catalog-toolbar__search">
          <input
            v-model="tagQuery"
            placeholder="按标签筛选，如：短剧, 男声"
            @keyup.enter="applyTagQuery"
          />
          <button class="btn btn--primary btn--sm" :disabled="loading" @click="applyTagQuery">搜索</button>
          <button
            v-if="selectedTags.length"
            class="text-action"
            :disabled="loading"
            @click="clearTagFilter"
          >
            清除
          </button>
        </div>
        <div v-if="availableTags.length" class="tag-chips catalog-toolbar__tags">
          <button
            v-for="t in availableTags"
            :key="t"
            type="button"
            class="tag-chip"
            :class="{ 'tag-chip--active': selectedTags.includes(t) }"
            @click="toggleTag(t)"
          >
            {{ t }}
          </button>
        </div>
      </div>

      <div v-if="featuredVoices.length" class="catalog-hero-grid">
        <article
          v-for="e in featuredVoices"
          :key="e.catalog_id"
          class="catalog-hero-card"
          role="button"
          tabindex="0"
          @click="goCatalog(e)"
          @keydown.enter="goCatalog(e)"
        >
          <div class="catalog-hero-card__head">
            <div class="catalog-hero-card__avatar" aria-hidden="true">{{ avatarInitial(e.title) }}</div>
            <div class="catalog-hero-card__meta">
              <span class="catalog-hero-card__badge">精选</span>
              <h2 class="catalog-hero-card__title">{{ e.title }}</h2>
              <p class="catalog-hero-card__desc">{{ e.description || e.voice_name }}</p>
            </div>
          </div>
          <div v-if="e.demo_audio_url" class="catalog-hero-card__player" @click.stop>
            <TapePlayer :src="e.demo_audio_url" :height="72" />
          </div>
          <div class="catalog-hero-card__foot" @click.stop>
            <div class="catalog-hero-card__actions row-actions">
              <button
                v-if="!isSelf"
                type="button"
                class="text-action text-action--accent"
                @click="goMessages(e.title)"
              >
                咨询此音色
              </button>
              <span v-if="!isSelf" class="row-actions__sep" aria-hidden="true">·</span>
              <button type="button" class="text-action" @click="goCatalog(e)">去音色馆</button>
            </div>
          </div>
        </article>
      </div>

      <ul v-if="otherVoices.length" class="catalog-grid catalog-grid--compact" style="margin-top: 16px">
        <li v-for="e in otherVoices" :key="e.catalog_id">
          <article class="voice-tile voice-tile--compact" role="button" tabindex="0" @click="goCatalog(e)">
            <div class="voice-tile__top">
              <div class="voice-tile__avatar" aria-hidden="true">{{ avatarInitial(e.title) }}</div>
              <div class="voice-tile__meta">
                <h3 class="voice-tile__title">{{ e.title }}</h3>
                <p class="voice-tile__desc">{{ e.description || e.voice_name }}</p>
              </div>
            </div>
            <div v-if="e.demo_audio_url" class="voice-tile__audio" @click.stop>
              <TapePlayer :src="e.demo_audio_url" :height="52" />
            </div>
            <div class="voice-tile__actions row-actions" @click.stop>
              <button v-if="!isSelf" type="button" class="text-action text-action--accent" @click="goMessages(e.title)">
                咨询
              </button>
              <span v-if="!isSelf" class="row-actions__sep" aria-hidden="true">·</span>
              <button type="button" class="text-action" @click="onDownloadDemo(e)">样音</button>
            </div>
          </article>
        </li>
      </ul>

      <div v-if="!profile?.voices.length" class="empty-state">
        <LoadingSpinner v-if="loading" inline text="加载创作者主页…" />
        <p v-else>该创作者暂无符合筛选的公开音色</p>
      </div>
      </RackPanel>

      <PageActionBar v-if="isSelf" label="创作者">
        <PageActionLink @click="openEdit">编辑主页</PageActionLink>
        <router-link to="/catalog" class="page-action-link">发布到音色馆</router-link>
      </PageActionBar>
    </PageSurface>

    <AppModal :open="showEdit" label="主页" title="编辑我的主页" @close="showEdit = false">
      <div class="form-stack">
        <label class="field">
          <span>展示昵称</span>
          <input v-model="editName" maxlength="64" />
        </label>
        <label class="field">
          <span>简介</span>
          <textarea v-model="editBio" rows="4" maxlength="500" />
        </label>
      </div>
      <template #footer>
        <button type="button" class="btn btn--ghost btn--sm" @click="showEdit = false">取消</button>
        <button type="button" class="btn btn--primary btn--sm" :disabled="saving" @click="onSaveProfile">
          {{ saving ? "保存中…" : "保存" }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.creator-page {
  gap: 12px;
}

.voice-tile__actions {
  margin-top: 10px;
}
</style>
