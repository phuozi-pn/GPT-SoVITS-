/**
 * AI Intelligence API client — LLM-powered smart features.
 */
import { apiJson } from "./client";

// ── Smart synthesis params ──────────────────────────────────────

export interface SmartSynthParamsResult {
  emotion: string;
  emotion_label: string;
  emotion_strength: number;
  speed_factor: number;
  temperature: number;
  pitch_factor: number;
  reasoning: string;
}

export interface SmartSynthParamsResponse {
  result: SmartSynthParamsResult;
  mode: "llm" | "fallback";
}

export async function recommendSynthParams(params: {
  text: string;
  character_hint?: string;
  context_hint?: string;
}): Promise<SmartSynthParamsResponse> {
  return apiJson<SmartSynthParamsResponse>("/api/v1/intelligence/synth-params", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// ── Smart voice matching ───────────────────────────────────────

export interface SmartVoiceMatchItem {
  voice_id: string;
  score: number;
  reason: string;
}

export interface SmartVoiceMatchResponse {
  matches: SmartVoiceMatchItem[];
  mode: "llm" | "fallback";
}

export async function matchVoice(params: {
  character_description: string;
  available_voices: Array<Record<string, unknown>>;
}): Promise<SmartVoiceMatchResponse> {
  return apiJson<SmartVoiceMatchResponse>("/api/v1/intelligence/match-voice", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// ── Smart emotion ──────────────────────────────────────────────

export interface SmartEmotionResult {
  emotion: string;
  emotion_label: string;
  strength: number;
  text_preview: string;
  mode: "llm" | "keyword";
}

export async function analyzeEmotionSmart(
  text: string,
  useLLM = true,
): Promise<SmartEmotionResult> {
  const params = new URLSearchParams({ text, use_llm: String(useLLM) });
  return apiJson<SmartEmotionResult>(`/api/v1/intelligence/emotion?${params}`, {
    method: "POST",
  });
}

// ── Content moderation ─────────────────────────────────────────

export interface SmartModerateResult {
  passed: boolean;
  risk_level: "low" | "medium" | "high";
  flags: string[];
  reason: string;
}

export interface SmartModerateResponse {
  result: SmartModerateResult;
  mode: "llm" | "rule";
}

export async function moderateContent(params: {
  text: string;
  context?: "post" | "message" | "profile" | "voice_description";
}): Promise<SmartModerateResponse> {
  return apiJson<SmartModerateResponse>("/api/v1/intelligence/moderate", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

// ── Voice description generation ───────────────────────────────

export interface GeneratedVoiceDescription {
  title: string;
  description: string;
  tags: string[];
  suitable_for: string[];
  mode: "llm" | "fallback";
}

export async function generateVoiceDescription(params: {
  voice_name: string;
  tags?: string[];
  sample_text?: string;
}): Promise<GeneratedVoiceDescription> {
  const searchParams = new URLSearchParams({ voice_name: params.voice_name });
  if (params.tags?.length) {
    searchParams.set("tags", params.tags.join(","));
  }
  if (params.sample_text) {
    searchParams.set("sample_text", params.sample_text);
  }
  return apiJson<GeneratedVoiceDescription>(
    `/api/v1/intelligence/voice-description?${searchParams}`,
    { method: "POST" },
  );
}

// ── Script polish ────────────────────────────────────────────────

export interface ScriptPolishResponse {
  polished_text: string;
  changes_summary: string;
  character_names: string[];
  line_count: number;
  mode: "llm" | "fallback";
}

export async function polishScript(params: {
  text: string;
  polish_scope?: "full" | "grammar" | "names" | "narration";
}): Promise<ScriptPolishResponse> {
  return apiJson<ScriptPolishResponse>("/api/v1/intelligence/polish-script", {
    method: "POST",
    body: JSON.stringify({
      text: params.text,
      polish_scope: params.polish_scope ?? "full",
    }),
  });
}
