<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  createDeveloperApiKey,
  fetchDeveloperApiKeys,
  revokeDeveloperApiKey,
  updateDeveloperApiKeyWebhook,
  type ApiKeySummary,
} from "@/api/developer";
import PageHero from "@/components/PageHero.vue";
import PageSurface from "@/components/PageSurface.vue";
import AppModal from "@/components/AppModal.vue";
import PageActionBar from "@/components/PageActionBar.vue";
import PageActionLink from "@/components/PageActionLink.vue";
import { formatApiError } from "@/utils/apiErrors";

const keys = ref<ApiKeySummary[]>([]);
const loading = ref(false);
const error = ref("");
const toast = ref("");
const newKeyName = ref("my-integration");
const createdKey = ref("");
const showCreate = ref(false);
const webhookKeyId = ref("");
const webhookUrl = ref("");
const webhookSecret = ref("");

async function reload() {
  loading.value = true;
  error.value = "";
  try {
    keys.value = await fetchDeveloperApiKeys();
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    loading.value = false;
  }
}

async function onCreate() {
  error.value = "";
  try {
    const res = await createDeveloperApiKey(newKeyName.value.trim() || "integration");
    createdKey.value = res.api_key;
    showCreate.value = true;
    await reload();
  } catch (e) {
    error.value = formatApiError(e);
  }
}

async function onRevoke(keyId: string) {
  if (!window.confirm("确定撤销此 API Key？")) return;
  try {
    await revokeDeveloperApiKey(keyId);
    toast.value = "已撤销";
    await reload();
  } catch (e) {
    error.value = formatApiError(e);
  }
}

function openWebhook(key: ApiKeySummary) {
  webhookKeyId.value = key.key_id;
  webhookUrl.value = key.webhook_url || "";
  webhookSecret.value = "";
}

async function saveWebhook() {
  if (!webhookKeyId.value) return;
  try {
    await updateDeveloperApiKeyWebhook(webhookKeyId.value, {
      webhook_url: webhookUrl.value.trim() || null,
      webhook_secret: webhookSecret.value.trim() || null,
    });
    toast.value = "Webhook 已保存";
    webhookKeyId.value = "";
    await reload();
  } catch (e) {
    error.value = formatApiError(e);
  }
}

onMounted(() => {
  void reload();
});
</script>

<template>
  <div class="page page--full">
    <div v-if="error" class="alert alert--error">{{ error }}</div>
    <div v-if="toast" class="alert alert--ok">{{ toast }}</div>

    <PageSurface>
      <PageHero compact flow title="开发者 API" hint="Open API 密钥与 Job 完成 Webhook（REQ-030）">
        <template #actions>
          <button class="btn btn--primary btn--sm" :disabled="loading" @click="reload">刷新</button>
        </template>
      </PageHero>

      <div class="dev-create">
        <label>
          密钥名称
          <input v-model="newKeyName" placeholder="my-integration" />
        </label>
        <button class="btn btn--primary btn--sm" type="button" @click="onCreate">创建 API Key</button>
      </div>

      <ul v-if="keys.length" class="grant-list">
        <li v-for="k in keys" :key="k.key_id">
          <span>
            {{ k.name }} · {{ k.key_prefix }}…
            <span v-if="k.revoked" class="pill pill--danger">已撤销</span>
            <span v-if="k.webhook_url" class="pill pill--ok">Webhook</span>
          </span>
          <span class="row-actions">
            <button class="text-action" type="button" @click="openWebhook(k)">Webhook</button>
            <span class="row-actions__sep" aria-hidden="true">·</span>
            <button
              v-if="!k.revoked"
              class="text-action text-action--danger"
              type="button"
              @click="onRevoke(k.key_id)"
            >
              撤销
            </button>
          </span>
        </li>
      </ul>
      <p v-else class="hint">{{ loading ? "加载中…" : "暂无 API Key" }}</p>

      <PageActionBar label="文档">
        <a class="page-action-link" href="http://127.0.0.1:8001/api/v1/docs" target="_blank" rel="noopener">
          OpenAPI 文档
        </a>
        <PageActionLink @click="$router.push('/admin')">运营台</PageActionLink>
      </PageActionBar>
    </PageSurface>

    <AppModal :open="showCreate" label="密钥" title="请立即保存 API Key" @close="showCreate = false">
      <p class="hint warn">完整密钥仅显示一次，请复制保存。</p>
      <pre class="dev-key">{{ createdKey }}</pre>
    </AppModal>

    <AppModal
      :open="!!webhookKeyId"
      label="Webhook"
      title="配置 Job 完成回调"
      @close="webhookKeyId = ''"
    >
      <div class="form-grid">
        <label class="span-2">
          Webhook URL
          <input v-model="webhookUrl" placeholder="https://example.com/hooks/voice-job" />
        </label>
        <label class="span-2">
          Webhook Secret（可选，用于 X-Webhook-Signature）
          <input v-model="webhookSecret" placeholder="your-secret" />
        </label>
      </div>
      <template #footer>
        <button class="btn btn--ghost btn--sm" type="button" @click="webhookKeyId = ''">取消</button>
        <button class="btn btn--primary btn--sm" type="button" @click="saveWebhook">保存</button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.dev-create {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: end;
  margin-bottom: 16px;
}

.dev-create label {
  display: grid;
  gap: 6px;
  min-width: 220px;
}

.dev-key {
  padding: 12px;
  border-radius: var(--radius-ui);
  background: rgb(0 0 0 / 0.25);
  word-break: break-all;
  font-family: var(--font-mono);
  font-size: 12px;
}
</style>
