import type { SmartSynthParamsResult } from "@/api/intelligence";
import type { ScriptSegment } from "@/modules/produce/types/script";

export const EMOTION_OPTIONS = [
  { value: "", label: "默认", icon: "—" },
  { value: "neutral", label: "中性", icon: "中" },
  { value: "happy", label: "喜悦", icon: "喜" },
  { value: "angry", label: "愤怒", icon: "怒" },
  { value: "sad", label: "哀伤", icon: "哀" },
  { value: "fearful", label: "恐惧", icon: "惧" },
  { value: "calm", label: "平静", icon: "静" },
] as const;

/** LLM pitch_factor 为半音偏移；合成后处理使用 0.5–1.5 倍率 */
export function semitonesToPitchMultiplier(semitones: number): number {
  const mult = 2 ** (semitones / 12);
  return Math.round(Math.max(0.5, Math.min(1.5, mult)) * 100) / 100;
}

export function applySmartSynthToSegment(
  segment: ScriptSegment,
  result: SmartSynthParamsResult,
): ScriptSegment {
  return {
    ...segment,
    emotion: result.emotion,
    emotionStrength: result.emotion_strength,
    speed: result.speed_factor,
    temperature: result.temperature,
    pitch: semitonesToPitchMultiplier(result.pitch_factor),
  };
}

export function formatSmartSynthHint(
  result: SmartSynthParamsResult,
  mode: "llm" | "fallback",
): string {
  const via = mode === "llm" ? "AI 语义分析" : "规则分析";
  return `${via}：${result.emotion_label} · 语速 ${result.speed_factor.toFixed(2)} · 温度 ${result.temperature.toFixed(2)} — ${result.reasoning}`;
}
