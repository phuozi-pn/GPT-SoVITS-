export class ApiError extends Error {
  code: string;
  status: number;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("access_token");
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function parseError(res: Response): Promise<ApiError> {
  let code = "HTTP_ERROR";
  let message = res.statusText;
  try {
    const body = await res.json();
    if (body.detail?.code) {
      code = body.detail.code;
      message = body.detail.message ?? message;
    } else if (body.message) {
      message = body.message;
    }
  } catch {
    /* ignore */
  }
  return new ApiError(res.status, code, message);
}

export async function apiJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  for (const [k, v] of Object.entries(authHeaders())) {
    headers.set(k, v);
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    throw await parseError(res);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

export interface QuotaSummary {
  chars_used: number;
  chars_remaining: number;
  monthly_char_limit: number;
  trainings_used: number;
  trainings_remaining: number;
  monthly_train_limit: number;
}

export interface LoginResponse {
  access_token: string;
  user: { user_id: string; phone: string };
  quota: QuotaSummary | null;
}

export interface JobResponse {
  job_id: string;
  job_type: string;
  status: string;
  error_message?: string | null;
  audio_url?: string | null;
  voice_version_id?: string | null;
  line_count?: number | null;
  succeeded_count?: number | null;
  failed_count?: number | null;
  zip_url?: string | null;
}

export async function sendSms(phone: string) {
  return apiJson<{ mock_code?: string | null; message: string }>("/api/v1/auth/sms/send", {
    method: "POST",
    body: JSON.stringify({ phone }),
  });
}

export async function login(phone: string, code: string) {
  return apiJson<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ phone, code }),
  });
}

export async function fetchQuota() {
  return apiJson<QuotaSummary>("/api/v1/usage/quota");
}

export async function createVoice(name: string) {
  return apiJson<{ voice_id: string; name: string }>("/api/v1/voices", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function createConsent(voiceId: string) {
  return apiJson<{ consent_id: string; status: string }>("/api/v1/consents", {
    method: "POST",
    body: JSON.stringify({ voice_id: voiceId }),
  });
}

export async function uploadAsset(voiceId: string, refText: string, file: File) {
  const form = new FormData();
  form.append("voice_id", voiceId);
  form.append("ref_text", refText);
  form.append("audio_file", file);
  return apiJson<{ asset_id: string; qc_passed: boolean; qc_result?: { issues?: { message: string }[] } }>(
    "/api/v1/voices/assets",
    { method: "POST", body: form },
  );
}

export async function confirmAsset(assetId: string) {
  return apiJson<{ asset_id: string; locked: boolean }>(
    `/api/v1/voices/assets/${assetId}/confirm`,
    { method: "POST" },
  );
}

export async function startTrain(voiceId: string, voiceAssetId: string) {
  return apiJson<{ job_id: string; status: string }>(`/api/v1/voices/${voiceId}/train`, {
    method: "POST",
    body: JSON.stringify({
      voice_asset_id: voiceAssetId,
      model_tag: "gsv-v2pro-20250606",
    }),
  });
}

export async function synthesize(voiceVersionId: string, text: string) {
  return apiJson<{ job_id: string; status: string }>("/api/v1/synthesis", {
    method: "POST",
    body: JSON.stringify({ voice_version_id: voiceVersionId, text, format: "wav" }),
  });
}

export async function getJob(jobId: string) {
  return apiJson<JobResponse>(`/api/v1/jobs/${jobId}`);
}

export async function pollJob(
  jobId: string,
  onTick?: (job: JobResponse) => void,
  timeoutMs = 600_000,
): Promise<JobResponse> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const job = await getJob(jobId);
    onTick?.(job);
    if (job.status === "succeeded" || job.status === "failed") {
      return job;
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error("任务超时，请稍后在任务 ID 处手动查询");
}
