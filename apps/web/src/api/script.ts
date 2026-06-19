import { ApiError } from "@/api/client";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("access_token");
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  let traceId = sessionStorage.getItem("trace_id");
  if (!traceId) {
    traceId = crypto.randomUUID();
    sessionStorage.setItem("trace_id", traceId);
  }
  headers["X-Trace-Id"] = traceId;
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  } else if (localStorage.getItem("dev_mode") === "1") {
    headers["X-User-Id"] =
      localStorage.getItem("dev_user_id") ?? "00000000-0000-0000-0000-000000000001";
  }
  return headers;
}

export type ParsedScreenplayLine = {
  character: string;
  text: string;
};

export type ScriptParseSmartResult = {
  mode: string;
  lines: ParsedScreenplayLine[];
  line_count: number;
  character_count: number;
};

export type ScriptParseStatus = {
  enabled: boolean;
  provider: string;
  model: string;
};

export async function fetchScriptParseStatus(): Promise<ScriptParseStatus> {
  const res = await fetch(`${API_BASE}/api/v1/script/parse-smart/status`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    throw new ApiError(res.status, "HTTP_ERROR", res.statusText);
  }
  return res.json();
}

/** 调用 DeepSeek 智能分段；LLM 未启用时返回 null（由调用方回退规则分段） */
export async function parseScriptSmart(text: string): Promise<ScriptParseSmartResult | null> {
  const res = await fetch(`${API_BASE}/api/v1/script/parse-smart`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ text }),
  });

  if (res.status === 503) {
    try {
      const body = await res.json();
      if (body.detail?.code === "LLM_DISABLED") return null;
    } catch {
      return null;
    }
  }

  if (!res.ok) {
    let code = "HTTP_ERROR";
    let message = res.statusText;
    try {
      const body = await res.json();
      if (body.detail?.code) {
        code = body.detail.code;
        message = body.detail.message ?? message;
      }
    } catch {
      // ignore
    }
    throw new ApiError(res.status, code, message);
  }

  return res.json();
}
