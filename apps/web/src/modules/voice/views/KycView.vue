<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { fetchKycStatus, submitKyc } from "@/api/kyc";
import AppModal from "@/components/AppModal.vue";
import PageActionBar from "@/components/PageActionBar.vue";
import PageActionLink from "@/components/PageActionLink.vue";
import PageHero from "@/components/PageHero.vue";
import PageSurface from "@/components/PageSurface.vue";
import { formatApiError } from "@/utils/apiErrors";

const router = useRouter();
const status = ref<Awaited<ReturnType<typeof fetchKycStatus>> | null>(null);
const realName = ref("");
const idNumber = ref("");
const busy = ref(false);
const error = ref("");
const success = ref("");
const showForm = ref(false);

onMounted(async () => {
  try {
    status.value = await fetchKycStatus();
  } catch (e) {
    error.value = formatApiError(e);
  }
});

async function onSubmit() {
  error.value = "";
  success.value = "";
  busy.value = true;
  try {
    const res = await submitKyc(realName.value.trim(), idNumber.value.trim());
    success.value = res.message;
    status.value = await fetchKycStatus();
    showForm.value = false;
  } catch (e) {
    error.value = formatApiError(e);
  } finally {
    busy.value = false;
  }
}

function goStudio() {
  router.push("/studio");
}
</script>

<template>
  <div class="page page--full kyc-page">
    <div v-if="error" class="alert alert--error">{{ error }}</div>
    <div v-if="success" class="alert alert--ok">{{ success }}</div>

    <PageSurface>
      <PageHero compact flow hint="训练前需完成实名；通过后可在训练工作台正常发起训练。">
      <template #stats>
        <p class="page-metrics">
          实名 <strong :class="status?.verified ? 'page-metrics__ok' : 'page-metrics__accent'">
            {{ status?.verified ? "已通过" : "未认证" }}
          </strong>
        </p>
      </template>
      </PageHero>

      <div class="status-banner" :class="status?.verified ? 'status-banner--ok' : 'status-banner--warn'">
      <div>
        <p v-if="status?.verified" class="hint" style="margin: 0">
          已通过实名认证 · 提供商 {{ status.provider ?? "mock" }} · 可正常发起训练
        </p>
        <p v-else class="hint" style="margin: 0">
          训练前需完成实名核验，否则接口将返回 403（KYC_REQUIRED）
        </p>
      </div>
      <button
        v-if="!status?.verified"
        type="button"
        class="btn btn--primary btn--sm"
        @click="showForm = true"
      >
        开始认证
      </button>
      <button v-else type="button" class="text-action" @click="goStudio">去训练工作台</button>
      </div>

      <PageActionBar label="相关">
        <PageActionLink v-if="!status?.verified" @click="showForm = true">提交认证</PageActionLink>
        <PageActionLink @click="goStudio">训练工作台</PageActionLink>
        <router-link to="/library" class="page-action-link">文本转语音</router-link>
      </PageActionBar>
    </PageSurface>

    <AppModal :open="showForm" label="KYC" title="实名认证" @close="showForm = false">
      <form class="form-stack" @submit.prevent="onSubmit">
        <label class="field">
          <span>真实姓名</span>
          <input v-model="realName" type="text" maxlength="32" required />
        </label>
        <label class="field">
          <span>身份证号</span>
          <input v-model="idNumber" type="text" maxlength="18" required placeholder="18 位" />
        </label>
        <p class="hint">未成年人身份证将被拒绝。测试可用：110101199001011234</p>
      </form>
      <template #footer>
        <button type="button" class="btn btn--ghost btn--sm" @click="showForm = false">取消</button>
        <button type="button" class="btn btn--primary btn--sm" :disabled="busy" @click="onSubmit">
          {{ busy ? "核验中…" : "提交 mock 核验" }}
        </button>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.kyc-page {
  max-width: 720px;
  gap: 12px;
}
</style>
