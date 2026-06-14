<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ApiError, pollJob } from "@/api/client";
import {
  bindProjectRole,
  createProject,
  fetchProjects,
  fetchVoiceVersions,
  submitBatchCsv,
  type ProjectSummary,
  type VoiceVersionSummary,
} from "@/api/library";

const projects = ref<ProjectSummary[]>([]);
const versions = ref<VoiceVersionSummary[]>([]);
const projectName = ref("短剧项目1");
const selectedProjectId = ref("");
const roleName = ref("龙宫");
const roleVoiceId = ref("");
const batchLog = ref("");
const zipUrl = ref("");
const error = ref("");
const busy = ref(false);

async function reload() {
  projects.value = await fetchProjects();
  versions.value = await fetchVoiceVersions();
  if (!selectedProjectId.value && projects.value.length) {
    selectedProjectId.value = projects.value[0].project_id;
  }
  if (!roleVoiceId.value && versions.value.length) {
    roleVoiceId.value = versions.value[0].voice_version_id;
  }
}

onMounted(async () => {
  try {
    await reload();
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});

async function onCreateProject() {
  error.value = "";
  busy.value = true;
  try {
    const p = await createProject(projectName.value.trim());
    selectedProjectId.value = p.project_id;
    await reload();
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : String(e);
  } finally {
    busy.value = false;
  }
}

async function onBindRole() {
  if (!selectedProjectId.value) return;
  error.value = "";
  busy.value = true;
  try {
    await bindProjectRole(selectedProjectId.value, roleName.value.trim(), roleVoiceId.value);
    await reload();
  } catch (e) {
    error.value = e instanceof ApiError ? e.message : String(e);
  } finally {
    busy.value = false;
  }
}

async function onCsvChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file || !selectedProjectId.value) return;
  error.value = "";
  zipUrl.value = "";
  batchLog.value = "上传 CSV…";
  busy.value = true;
  try {
    const res = await submitBatchCsv(selectedProjectId.value, file);
    batchLog.value = `批量任务 ${res.job_id}，${res.line_count} 行`;
    const job = await pollJob(
      res.job_id,
      (j) => {
        batchLog.value = `状态 ${j.status}`;
      },
      600_000,
    );
    if (job.status !== "succeeded") {
      throw new Error(job.error_message ?? "批量失败");
    }
    zipUrl.value = (job as { zip_url?: string }).zip_url ?? "";
    batchLog.value = `完成：成功 ${(job as { succeeded_count?: number }).succeeded_count ?? "?"} 行`;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    busy.value = false;
    input.value = "";
  }
}

const currentProject = () => projects.value.find((p) => p.project_id === selectedProjectId.value);
</script>

<template>
  <div>
    <header class="page-hero">
      <h1>批量配音</h1>
      <p>创建项目 → 绑定角色音色 → 上传 CSV（列：role, text 或 角色, 台词）</p>
    </header>

    <div v-if="error" class="alert alert--error">{{ error }}</div>

    <section class="card">
      <h2>1. 项目</h2>
      <div class="row">
        <input v-model="projectName" placeholder="项目名称" />
        <button class="btn btn--primary" :disabled="busy" @click="onCreateProject">新建</button>
      </div>
      <label>
        当前项目
        <select v-model="selectedProjectId">
          <option v-for="p in projects" :key="p.project_id" :value="p.project_id">{{ p.name }}</option>
        </select>
      </label>
    </section>

    <section class="card">
      <h2>2. 角色绑定</h2>
      <div class="form-grid">
        <label>角色名<input v-model="roleName" /></label>
        <label>
          音色版本
          <select v-model="roleVoiceId">
            <option v-for="v in versions" :key="v.voice_version_id" :value="v.voice_version_id">
              {{ v.voice_name }} v{{ v.version }}
            </option>
          </select>
        </label>
      </div>
      <button class="btn btn--primary" :disabled="busy || !selectedProjectId" @click="onBindRole">绑定</button>
      <ul v-if="currentProject()?.roles.length" class="roles">
        <li v-for="r in currentProject()!.roles" :key="r.role_id">
          {{ r.role_name }} → {{ r.voice_version_id.slice(0, 8) }}…
        </li>
      </ul>
    </section>

    <section class="card">
      <h2>3. CSV 批量合成</h2>
      <p class="hint">示例：<code>role,text</code> 行：<code>龙宫,方源，你给我出来！</code></p>
      <input type="file" accept=".csv,text/csv" :disabled="busy" @change="onCsvChange" />
      <p v-if="batchLog" class="log">{{ batchLog }}</p>
      <p v-if="zipUrl">
        <a class="btn btn--primary" :href="zipUrl" download>下载 ZIP 分轨</a>
      </p>
    </section>
  </div>
</template>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem;
  margin-top: 1.25rem;
}
.row {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}
label {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.85rem;
}
input,
select {
  padding: 0.5rem 0.65rem;
  border: 1px solid var(--border);
  border-radius: 8px;
}
.roles {
  margin: 0.75rem 0 0;
  padding-left: 1.2rem;
  font-size: 0.9rem;
}
.hint {
  font-size: 0.85rem;
  color: var(--text-muted);
}
.log {
  margin-top: 0.75rem;
  font-family: var(--font-mono, monospace);
  font-size: 0.85rem;
}
</style>
