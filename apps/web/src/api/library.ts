import { apiJson, type JobResponse } from "./client";

export interface VoiceVersionSummary {
  voice_version_id: string;
  voice_id: string;
  voice_name: string;
  version: number;
  model_tag: string;
  label?: string | null;
  ref_text?: string | null;
  imported?: boolean;
}

export interface ProjectRole {
  role_id: string;
  project_id: string;
  role_name: string;
  voice_version_id: string;
}

export interface ProjectSummary {
  project_id: string;
  name: string;
  roles: ProjectRole[];
}

export interface BatchJobResponse extends JobResponse {
  line_count?: number | null;
  succeeded_count?: number | null;
  failed_count?: number | null;
  zip_url?: string | null;
}

export async function fetchVoiceVersions() {
  return apiJson<VoiceVersionSummary[]>("/api/v1/voice-versions");
}

export interface ImportWeightsBody {
  voice_name: string;
  label?: string;
  engine_gpt_weights: string;
  engine_sovits_weights: string;
  ref_audio_host_path: string;
  ref_text: string;
  text_split_method?: string;
  temperature?: number;
  speed_factor?: number;
  top_p?: number;
}

export async function importEngineWeights(body: ImportWeightsBody) {
  return apiJson<VoiceVersionSummary>("/api/v1/voices/import-weights", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchProjects() {
  return apiJson<ProjectSummary[]>("/api/v1/projects");
}

export async function createProject(name: string) {
  return apiJson<ProjectSummary>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function bindProjectRole(projectId: string, roleName: string, voiceVersionId: string) {
  return apiJson<ProjectRole>(`/api/v1/projects/${projectId}/roles`, {
    method: "POST",
    body: JSON.stringify({ role_name: roleName, voice_version_id: voiceVersionId }),
  });
}

export async function submitBatchCsv(projectId: string, file: File) {
  const form = new FormData();
  form.append("file", file);
  return apiJson<{ job_id: string; status: string; line_count: number }>(
    `/api/v1/projects/${projectId}/batch`,
    { method: "POST", body: form },
  );
}
