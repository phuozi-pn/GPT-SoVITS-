<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { fetchAuthorizationVerify } from "@/api/catalog";
import PageSurface from "@/components/PageSurface.vue";
import RackPanel from "@/modules/voice/components/studio/RackPanel.vue";
import { formatApiError } from "@/utils/apiErrors";
import { useIsShowcaseVisitor } from "@/composables/useAppShell";
import ShareLink from "@/modules/public/components/ShareLink.vue";
import PublicPageHead from "@/modules/public/components/PublicPageHead.vue";
import { setPageMeta } from "@/utils/pageMeta";

const route = useRoute();
const loading = ref(false);
const error = ref("");
const isShowcaseVisitor = useIsShowcaseVisitor();
const result = ref<{
  authorization_id: string;
  status: string;
  valid: boolean;
  voice_title: string;
  license_type: string;
  message: string;
} | null>(null);

const authorizationId = computed(() => String(route.params.authorizationId ?? ""));

async function load() {
  if (!authorizationId.value) return;
  loading.value = true;
  error.value = "";
  result.value = null;
  try {
    result.value = await fetchAuthorizationVerify(authorizationId.value);
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
}

watch(
  () => result.value,
  (r) => {
    if (!r) return;
    const status = r.valid ? "有效" : "无效";
    const title = `授权${status} · ${r.voice_title} · Voice Studio`;
    setPageMeta(title, r.message || `授权凭证 ${r.authorization_id.slice(0, 8)}… 验真结果为${status}`);
  },
);

onMounted(load);
watch(authorizationId, load);
</script>

<template>
  <!-- 访客展示壳 -->
  <div v-if="isShowcaseVisitor" class="showcase-verify">
    <PublicPageHead title="授权验真" hint="第三方平台可查询授权凭证是否仍然有效">
      <template #actions>
        <ShareLink label="复制验真链接" copied-label="已复制链接" />
      </template>
    </PublicPageHead>

    <div v-if="error" class="alert alert--error">{{ error }}</div>

    <article class="showcase-verify__card showcase-certificate" aria-label="授权证书夹">
      <p v-if="loading" class="hint">查询中…</p>
      <template v-else-if="result">
        <header class="showcase-certificate__head">
          <p class="showcase-certificate__eyebrow">VOICE STUDIO · AUTHORIZATION</p>
          <div class="verify-badge" :class="result.valid ? 'verify-badge--ok' : 'verify-badge--bad'">
            {{ result.valid ? "授权有效" : "授权无效" }}
          </div>
          <p class="showcase-certificate__title">{{ result.voice_title || "—" }}</p>
        </header>

        <div class="showcase-certificate__grid">
          <section class="showcase-certificate__panel">
            <dl class="verify-dl">
              <dt>授权 ID</dt>
              <dd class="mono">{{ result.authorization_id }}</dd>
              <dt>授权类型</dt>
              <dd>{{ result.license_type || "—" }}</dd>
              <dt>状态</dt>
              <dd>{{ result.status }}</dd>
            </dl>
          </section>

          <section class="showcase-certificate__panel showcase-certificate__panel--note">
            <p class="rack-label">说明</p>
            <p class="showcase-certificate__note">{{ result.message }}</p>
          </section>
        </div>
      </template>
      <p v-else class="hint">请提供有效的授权 ID</p>
    </article>

    <div class="showcase-verify__foot row-actions">
      <RouterLink to="/browse" class="text-action">浏览音色馆</RouterLink>
      <span class="row-actions__sep" aria-hidden="true">·</span>
      <RouterLink to="/" class="text-action">返回首页</RouterLink>
    </div>
  </div>

  <!-- 工作台内 -->
  <div v-else class="page page--full verify-page">
    <div v-if="error" class="alert alert--error">{{ error }}</div>

    <PageSurface>
      <PublicPageHead title="授权验真" hint="核验 PDF 凭证中的授权 ID 是否仍然有效">
        <template #actions>
          <ShareLink label="复制验真链接" copied-label="已复制链接" />
        </template>
      </PublicPageHead>

      <RackPanel label="验真" title="查询结果">
        <p v-if="loading" class="hint">查询中…</p>
        <template v-else-if="result">
          <div class="verify-badge" :class="result.valid ? 'verify-badge--ok' : 'verify-badge--bad'">
            {{ result.valid ? "授权有效" : "授权无效" }}
          </div>
          <dl class="verify-dl">
            <dt>授权 ID</dt>
            <dd class="mono">{{ result.authorization_id }}</dd>
            <dt>音色</dt>
            <dd>{{ result.voice_title || "—" }}</dd>
            <dt>授权类型</dt>
            <dd>{{ result.license_type || "—" }}</dd>
            <dt>状态</dt>
            <dd>{{ result.status }}</dd>
            <dt>说明</dt>
            <dd>{{ result.message }}</dd>
          </dl>
        </template>
        <p v-else class="hint">请提供有效的授权 ID</p>

        <div class="row-actions" style="margin-top: 16px">
          <RouterLink to="/catalog" class="text-action">返回音色馆</RouterLink>
          <span class="row-actions__sep" aria-hidden="true">·</span>
          <RouterLink to="/browse" class="text-action">公开站点</RouterLink>
        </div>
      </RackPanel>
    </PageSurface>
  </div>
</template>

<style scoped>
.verify-badge {
  display: inline-block;
  margin-bottom: 16px;
  padding: 8px 16px;
  border-radius: var(--radius-ui);
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
}

.verify-badge--ok {
  background: rgb(80 140 90 / 0.15);
  color: #3d6b45;
}

.verify-badge--bad {
  background: rgb(199 93 77 / 0.15);
  color: var(--color-peak-red);
}

.verify-dl {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 8px 16px;
  margin: 0;
  font-size: 14px;
}

.verify-dl dt {
  color: var(--color-brushed-dark);
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.verify-dl dd {
  margin: 0;
}

.mono {
  font-family: var(--font-mono);
  font-size: 12px;
  word-break: break-all;
}
</style>
