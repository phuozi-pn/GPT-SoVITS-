<script setup lang="ts">
import { onMounted, ref } from "vue";
import {
  fetchCloudGpuProfile,
  saveCloudGpuProfile,
  testCloudGpuConnection,
  type CloudGpuProfileSaveBody,
} from "@/api/cloudTrain";
import { formatApiError } from "@/utils/apiErrors";

const props = defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{
  connected: [ok: boolean];
}>();

const form = ref<CloudGpuProfileSaveBody>({
  ssh_host: "",
  ssh_port: 22,
  ssh_user: "root",
  password: "",
  remote_engine_root: "/root/autodl-tmp/GPT-SoVITS",
  remote_platform_root: "/root/autodl-tmp/GPT",
  remote_work_dir: "/root/autodl-tmp/cloud_train_jobs",
});

const busy = ref(false);
const message = ref("");
const ok = ref<boolean | null>(null);
const loaded = ref(false);

onMounted(async () => {
  try {
    const profile = await fetchCloudGpuProfile();
    if (profile) {
      form.value.ssh_host = profile.ssh_host;
      form.value.ssh_port = profile.ssh_port;
      form.value.ssh_user = profile.ssh_user;
      form.value.remote_engine_root = profile.remote_engine_root;
      form.value.remote_platform_root = profile.remote_platform_root;
      form.value.remote_work_dir = profile.remote_work_dir;
      ok.value = profile.last_test_ok ?? null;
      emit("connected", Boolean(profile.has_credential && profile.last_test_ok));
    }
  } catch {
    /* dev */
  } finally {
    loaded.value = true;
  }
});

async function onTest() {
  busy.value = true;
  message.value = "";
  try {
    const result = await testCloudGpuConnection(form.value);
    ok.value = result.ok;
    message.value = result.message;
    emit("connected", result.ok);
  } catch (e) {
    ok.value = false;
    message.value = formatApiError(e);
    emit("connected", false);
  } finally {
    busy.value = false;
  }
}

async function onSave() {
  busy.value = true;
  message.value = "";
  try {
    const saved = await saveCloudGpuProfile(form.value);
    const test = await testCloudGpuConnection({
      ...form.value,
      password: form.value.password,
    });
    ok.value = test.ok;
    message.value = test.ok ? "已保存并验证连接成功" : test.message;
    emit("connected", test.ok);
    if (!form.value.password && saved.has_credential) {
      message.value = test.ok ? "已保存（使用已存密码）并验证成功" : test.message;
    }
  } catch (e) {
    ok.value = false;
    message.value = formatApiError(e);
    emit("connected", false);
  } finally {
    busy.value = false;
  }
}

defineExpose({ form, ok });
</script>

<template>
  <div v-if="loaded" class="cloud-gpu-form">
    <div class="cloud-gpu-form__head">
      <p class="field-hint" style="margin: 0">
        填写 AutoDL / 租用 GPU 的 SSH 信息。密码加密保存，仅用于训练连接。
      </p>
      <span
        v-if="ok === true"
        class="studio-chip studio-chip--ok"
      >已验证</span>
      <span
        v-else-if="ok === false"
        class="studio-chip studio-chip--warn"
      >未连接</span>
    </div>
    <div class="field">
      <span class="field-label">SSH 主机</span>
      <input v-model="form.ssh_host" class="input" placeholder="connect.autodl.xyz" :disabled="disabled || busy" />
    </div>
    <div class="row" style="gap: 0.5rem; margin-top: 0.5rem">
      <label class="field" style="flex: 1">
        <span class="field-label">端口</span>
        <input v-model.number="form.ssh_port" class="input" type="number" :disabled="disabled || busy" />
      </label>
      <label class="field" style="flex: 1">
        <span class="field-label">用户名</span>
        <input v-model="form.ssh_user" class="input" :disabled="disabled || busy" />
      </label>
    </div>
    <div class="field" style="margin-top: 0.5rem">
      <span class="field-label">SSH 密码</span>
      <input
        v-model="form.password"
        class="input"
        type="password"
        autocomplete="off"
        placeholder="留空则沿用已保存密码"
        :disabled="disabled || busy"
      />
    </div>
    <details style="margin-top: 0.65rem">
      <summary class="field-hint">远端目录（AutoDL 默认如下，训练数据在「工作目录 / job_id / dataset」）</summary>
      <div class="field" style="margin-top: 0.5rem">
        <span class="field-label">GPT-SoVITS 目录</span>
        <input v-model="form.remote_engine_root" class="input" :disabled="disabled || busy" />
      </div>
      <div class="field" style="margin-top: 0.35rem">
        <span class="field-label">平台脚本目录</span>
        <input v-model="form.remote_platform_root" class="input" :disabled="disabled || busy" />
      </div>
      <div class="field" style="margin-top: 0.35rem">
        <span class="field-label">训练工作目录</span>
        <input v-model="form.remote_work_dir" class="input" :disabled="disabled || busy" />
      </div>
    </details>
    <p v-if="message" class="field-hint" :class="{ 'text-ok': ok, 'text-err': ok === false }" style="margin-top: 0.5rem">
      {{ message }}
    </p>
    <div class="row" style="margin-top: 0.65rem; gap: 0.5rem">
      <button type="button" class="btn btn--ghost" :disabled="disabled || busy" @click="onTest">测试连接</button>
      <button type="button" class="btn btn--primary" :disabled="disabled || busy" @click="onSave">保存并验证</button>
    </div>
  </div>
</template>

<style scoped>
.cloud-gpu-form__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.65rem;
}

.text-ok {
  color: #3d8b5f;
}
.text-err {
  color: #c45c5c;
}

.studio-chip {
  display: inline-block;
  font-size: 0.72rem;
  padding: 0.12rem 0.45rem;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
}

.studio-chip--ok {
  background: rgba(61, 139, 95, 0.15);
  color: #3d8b5f;
}

.studio-chip--warn {
  background: rgba(196, 92, 92, 0.12);
  color: #c45c5c;
}

.studio-chip--muted {
  background: rgba(255, 255, 255, 0.06);
  opacity: 0.75;
}
</style>
