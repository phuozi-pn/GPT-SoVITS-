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
  downloadCatalogAsset,
  generateCreatorAvatar,
  updateMyProfile,
} from "@/api/social";
import AppModal from "@/components/AppModal.vue";
import CreatorAvatar from "@/components/CreatorAvatar.vue";
import CatalogAvatar from "@/components/CatalogAvatar.vue";
import CatalogHeroCard from "@/components/CatalogHeroCard.vue";
import LoadingSpinner from "@/components/LoadingSpinner.vue";
import PageActionBar from "@/components/PageActionBar.vue";
import PageActionLink from "@/components/PageActionLink.vue";
import PageSurface from "@/components/PageSurface.vue";
import RackPanel from "@/modules/voice/components/studio/RackPanel.vue";
import TapePlayer from "@/modules/voice/components/studio/TapePlayer.vue";
import { useAppShell } from "@/composables/useAppShell";
import { useCopyText } from "@/composables/useCopyText";
import { formatApiError } from "@/utils/apiErrors";
import { catalogAppPath, loginToCatalogQuery } from "@/utils/catalogLinks";
import { hasAppSession } from "@/utils/session";
import { setPageMeta } from "@/utils/pageMeta";

const route = useRoute();
const router = useRouter();
const shell = useAppShell();
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
const editAvatarUrl = ref("");
const editIsPublic = ref(true);
const avatarGenerating = ref(false);
const avatarGenError = ref("");
const saving = ref(false);
const showEdit = ref(false);
const publicSelectedId = ref("");

const inWorkbench = computed(() => shell.value === "workbench");
const hasSession = computed(() => hasAppSession());
const userId = computed(() => String(route.params.userId ?? ""));
const isSelf = computed(() => userId.value === getDevUserId());
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
  if (selectedTags.value.length) q.tags = selectedTags.value.join(",");
  else delete q.tags;
  router.replace({ query: q });
}

function toggleTag(tag: string) {
  const idx = selectedTags.value.indexOf(tag);
  if (idx >= 0) selectedTags.value.splice(idx, 1);
  else selectedTags.value.push(tag);
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

function goMessages(voiceTitle?: string) {
  const query: Record<string, string> = { peer: userId.value };
  if (voiceTitle) query.draft = `你好，想咨询「${voiceTitle}」的授权与合作。`;
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
  if (hasSession.value) goMessages(voiceTitle);
  else goLoginMessage(voiceTitle);
}

function goCatalog(entry: CatalogEntry | string) {
  const catalogId = typeof entry === "string" ? entry : entry.catalog_id;
  if (inWorkbench.value) router.push(catalogAppPath(catalogId));
  else router.push({ path: "/browse", query: { pick: catalogId } });
}

function goCatalogHub() {
  router.push(inWorkbench.value ? "/catalog" : "/browse");
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
    await updateMyProfile({
      display_name: editName.value.trim(),
      bio: editBio.value.trim(),
      avatar_url: editAvatarUrl.value.trim() || null,
      is_public: editIsPublic.value,
    });
    success.value = "主页已更新";
    showEdit.value = false;
    await loadProfile();
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    saving.value = false;
  }
}

async function onGenerateAvatar() {
  avatarGenError.value = "";
  avatarGenerating.value = true;
  try {
    const res = await generateCreatorAvatar();
    editAvatarUrl.value = res.avatar_url;
    success.value = "头像已生成，记得保存";
  } catch (e) {
    avatarGenError.value = formatApiError(e);
  } finally {
    avatarGenerating.value = false;
  }
}

function openEdit() {
  if (profile.value) {
    editName.value = profile.value.display_name;
    editBio.value = profile.value.bio ?? "";
    editAvatarUrl.value = profile.value.avatar_url ?? "";
  }
  avatarGenError.value = "";
  showEdit.value = true;
}

async function onDownloadDemo(entry: CatalogEntry) {
  try {
    await downloadCatalogAsset(catalogDemoDownloadUrl(entry.catalog_id), `${entry.title}_demo.wav`);
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
      editAvatarUrl.value = profile.value.avatar_url ?? "";
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

watch(() => route.params.userId, () => void loadProfile());

watch(
  () => profile.value,
  (p) => {
    if (!p || inWorkbench.value) return;
    setPageMeta(
      `${p.display_name} · 创作者 · Voice Studio`,
      p.bio?.trim() || `公开音色 ${p.published_count} 个 · 在 Voice Studio 浏览授权与试听样音`,
    );
  },
);
</script>

<template>
  <div :class="inWorkbench ? 'page page--full creator-page' : 'showcase-creator'">
    <div v-if="error" class="alert alert--error">{{ error }}</div>
    <div v-if="success && inWorkbench" class="alert alert--ok">{{ success }}</div>

    <component :is="inWorkbench ? PageSurface : 'div'">
      <p v-if="loading && !profile" class="hint">加载创作者主页…</p>

      <div
        v-if="profile"
        class="creator-profile-hero"
        :class="{ 'creator-profile-hero--showcase': !inWorkbench }"
      >
        <div class="creator-profile-hero__avatar-wrap">
          <CreatorAvatar
            :display-name="profile.display_name"
            :avatar-url="profile.avatar_url"
            :user-id="profile.user_id"
            size="lg"
          />
        </div>
        <div class="creator-profile-hero__copy">
          <p v-if="!inWorkbench" class="showcase-creator__eyebrow">创作者</p>
          <h1 class="creator-profile-hero__name">{{ profile.display_name }}</h1>
          <p class="creator-profile-hero__bio">{{ profile.bio || "这位创作者还没有填写简介" }}</p>
          <p class="showcase-creator__stats hint">
            公开音色 <strong>{{ profile.published_count }}</strong>
            <template v-if="featuredVoices.length"> · 精选 <strong>{{ featuredVoices.length }}</strong></template>
          </p>
        </div>
        <div class="creator-profile-hero__actions row-actions">
          <button type="button" class="text-action" @click="shareCreatorPage">
            {{ shareCopied ? "已复制链接" : "分享主页" }}
          </button>
          <span class="row-actions__sep" aria-hidden="true">·</span>
          <button type="button" class="text-action" @click="goCatalogHub">音色馆</button>
          <template v-if="isSelf">
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <button type="button" class="text-action" @click="openEdit">编辑主页</button>
          </template>
          <template v-else-if="hasSession">
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <button type="button" class="text-action text-action--accent" @click="contactCreator()">发私信</button>
          </template>
          <template v-else>
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <button type="button" class="text-action text-action--accent" @click="contactCreator()">登录后私信</button>
          </template>
          <template v-if="inWorkbench && hasSession && !isSelf">
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <router-link to="/community" class="text-action">消息</router-link>
          </template>
        </div>
      </div>

      <RackPanel v-if="profile" :label="inWorkbench ? '作品' : undefined" :title="inWorkbench ? '公开音色' : undefined">
        <section :class="inWorkbench ? undefined : 'showcase-section'">
          <h2 v-if="!inWorkbench" class="showcase-section__title">公开作品</h2>

          <div :class="inWorkbench ? 'catalog-toolbar' : 'showcase-browse__toolbar'">
            <div :class="inWorkbench ? 'filter-bar catalog-toolbar__search' : undefined">
              <input
                v-model="tagQuery"
                placeholder="按标签筛选，如：短剧, 男声"
                @keyup.enter="applyTagQuery"
              />
              <button
                type="button"
                class="btn btn--primary btn--sm"
                :disabled="loading"
                @click="applyTagQuery"
              >
                搜索
              </button>
              <button
                v-if="selectedTags.length"
                type="button"
                class="text-action"
                :disabled="loading"
                @click="clearTagFilter"
              >
                清除
              </button>
            </div>
            <div
              v-if="availableTags.length"
              class="tag-chips"
              :class="{ 'catalog-toolbar__tags': inWorkbench }"
              :style="!inWorkbench ? { marginBottom: '16px' } : undefined"
            >
              <button
                v-for="t in (inWorkbench ? availableTags : availableTags.slice(0, 12))"
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

          <div v-if="featuredVoices.length" :class="inWorkbench ? 'catalog-hero-grid catalog-hero-grid--stack' : 'showcase-creator__featured'">
            <template v-if="inWorkbench">
              <CatalogHeroCard
                v-for="e in featuredVoices"
                :key="e.catalog_id"
                :entry="e"
                :show-contact="false"
                :tag-limit="5"
                @select="goCatalog"
                @load-catalog="loadProfile"
              >
                <template #actions>
                  <button type="button" class="btn btn--primary btn--sm" @click.stop="goCatalog(e.catalog_id)">
                    试听合成
                  </button>
                  <button type="button" class="text-action text-action--accent" @click.stop="goCatalog(e.catalog_id)">
                    去音色馆
                  </button>
                  <template v-if="!isSelf">
                    <span class="row-actions__sep" aria-hidden="true">·</span>
                    <button type="button" class="text-action" @click.stop="contactCreator(e.title)">咨询授权</button>
                  </template>
                </template>
              </CatalogHeroCard>
            </template>
            <template v-else>
              <article
                v-for="e in featuredVoices"
                :key="e.catalog_id"
                class="showcase-creator__featured-card"
              >
              <div class="showcase-creator__featured-head">
                <span class="showcase-case__tag">精选</span>
                <h3 class="showcase-preview__title">{{ e.title }}</h3>
                <p class="hint">{{ e.description || e.voice_name }}</p>
              </div>
              <div v-if="e.demo_audio_url" @click.stop>
                <TapePlayer :src="e.demo_audio_url" :height="72" />
              </div>
              <p v-else class="hint">暂无样音</p>
              <div class="row-actions showcase-creator__featured-actions" @click.stop>
                <button type="button" class="text-action text-action--accent" @click="goCatalog(e.catalog_id)">
                  试听详情 →
                </button>
                <span v-if="!isSelf" class="row-actions__sep" aria-hidden="true">·</span>
                <button v-if="!isSelf" type="button" class="text-action" @click="contactCreator(e.title)">
                  咨询授权
                </button>
              </div>
              </article>
            </template>
          </div>

          <div
            v-if="otherVoices.length"
            :class="inWorkbench ? 'catalog-more' : 'showcase-browse__layout'"
            :style="!inWorkbench ? { marginTop: '8px' } : undefined"
          >
            <h3 v-if="inWorkbench" class="catalog-more__title">
              更多作品
              <span class="hint">（{{ otherVoices.length }}）</span>
            </h3>
            <div v-if="inWorkbench" class="catalog-hero-grid catalog-hero-grid--stack">
              <CatalogHeroCard
                v-for="e in otherVoices"
                :key="e.catalog_id"
                :entry="e"
                :show-contact="false"
                :tag-limit="5"
                @select="goCatalog"
                @load-catalog="loadProfile"
              >
                <template #actions>
                  <button type="button" class="btn btn--primary btn--sm" @click.stop="goCatalog(e.catalog_id)">
                    试听合成
                  </button>
                  <button type="button" class="text-action text-action--accent" @click.stop="goCatalog(e.catalog_id)">
                    去音色馆
                  </button>
                  <template v-if="!isSelf">
                    <span class="row-actions__sep" aria-hidden="true">·</span>
                    <button type="button" class="text-action" @click.stop="contactCreator(e.title)">咨询授权</button>
                  </template>
                </template>
              </CatalogHeroCard>
            </div>

            <template v-else>
              <ul class="showcase-browse__list">
                <li v-for="e in otherVoices" :key="e.catalog_id">
                  <button
                    type="button"
                    class="showcase-voice-tile"
                    :class="{ 'showcase-voice-tile--on': publicSelectedId === e.catalog_id }"
                    @click="selectPublicVoice(e.catalog_id)"
                  >
                    <CatalogAvatar :entry="e" size="sm" class="showcase-voice-tile__avatar-wrap" />
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
                <TapePlayer
                  v-if="publicSelected.demo_audio_url"
                  :src="publicSelected.demo_audio_url"
                  :height="88"
                />
                <p v-else class="hint">暂无样音</p>
                <p class="hint" style="margin-top: 12px">{{ formatPriceCents(publicSelected.price_cents) }}</p>
                <div class="showcase-browse__detail-actions">
                  <button
                    v-if="hasSession"
                    type="button"
                    class="btn btn--primary btn--sm"
                    @click="goCatalog(publicSelected)"
                  >
                    去音色馆购买 / 合成
                  </button>
                  <button v-else type="button" class="btn btn--primary btn--sm" @click="goLoginForCatalog(publicSelected)">
                    登录后购买 / 合成
                  </button>
                  <span class="row-actions" style="margin-left: 12px">
                    <button
                      type="button"
                      class="text-action text-action--accent"
                      @click="contactCreator(publicSelected.title)"
                    >
                      咨询
                    </button>
                  </span>
                </div>
              </aside>
            </template>
          </div>

          <div v-if="!profile.voices.length" class="empty-state">
            <LoadingSpinner v-if="loading" inline text="加载创作者主页…" />
            <p v-else><strong>暂无符合筛选的公开音色</strong></p>
          </div>
        </section>
      </RackPanel>

      <PageActionBar v-if="inWorkbench && isSelf" label="创作者">
        <PageActionLink @click="openEdit">编辑主页</PageActionLink>
        <router-link to="/catalog" class="page-action-link">发布到音色馆</router-link>
      </PageActionBar>
    </component>

    <AppModal :open="showEdit" label="主页" title="编辑我的主页" @close="showEdit = false">
      <div class="form-stack">
        <div class="creator-edit-avatar">
          <CreatorAvatar
            :display-name="editName || profile?.display_name || '创作者'"
            :avatar-url="editAvatarUrl"
            :user-id="profile?.user_id"
            size="lg"
          />
          <div class="creator-edit-avatar__actions">
            <button
              type="button"
              class="btn btn--ghost btn--sm"
              :disabled="avatarGenerating || saving"
              @click="onGenerateAvatar"
            >
              {{ avatarGenerating ? "AI 生成中…" : "AI 生成头像" }}
            </button>
            <p v-if="avatarGenError" class="hint warn">{{ avatarGenError }}</p>
            <p v-else class="hint">根据昵称与简介调用通义万相生成；生成后点保存生效。</p>
          </div>
        </div>
        <label class="field">
          <span>展示昵称</span>
          <input v-model="editName" maxlength="64" />
        </label>
        <label class="field">
          <span>简介</span>
          <textarea v-model="editBio" rows="4" maxlength="500" />
        </label>
        <label class="field field--row">
          <input v-model="editIsPublic" type="checkbox" />
          <span>公开主页（出现在创作者目录与发现页）</span>
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

.creator-edit-avatar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 8px;
}

.creator-edit-avatar__actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.voice-tile__actions {
  margin-top: 10px;
}

.field--row {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
